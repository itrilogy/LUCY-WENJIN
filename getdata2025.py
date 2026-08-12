# -*- coding: utf-8 -*-


import requests
import json
import threading
from threading import Thread
from dbconn2025 import DBConn
from datetime import datetime
import urllib.request
from urllib.parse import urlparse
import sys
import base64
import os
import time
import math


def main():
    """命令行入口：python3 getdata2025.py [步骤名]
    
    步骤名:
        test        单校测试（默认）
        getAll      全部步骤依次执行
        school      抓学校清单 (getAllSchool)
        score       抓录取分数线 (insertSchoolScore)
        major       抓专业分数线 (getMajorScoreNear5Byhread)
        plan        抓招生计划 (getCollegePlan)
    """
    steps = {
        "school": getAllSchool,
        "score": insertSchoolScore,
        "major": lambda: getMajorScoreNear5Byhread("江西"),
        "plan": getCollegePlan,
        "test": lambda: [create_tables(), getMajorScore("南昌大学", "江西", 2024, "物理类")][-1],
        "getAll": lambda: [
            create_tables(),
            getAllSchool(),
            insertSchoolScore(),
            getMajorScoreNear5Byhread("江西"),
            getCollegePlan()
        ],
    }
    
    step = sys.argv[1] if len(sys.argv) > 1 else "test"
    
    if step == "getAll":
        print("=" * 50)
        print("开始全量爬取：建表 → 学校清单 → 录取分 → 专业分 → 招生计划")
        print("=" * 50)
        create_tables()
        print("\n--- 第1步：学校清单 ---")
        getAllSchool()
        print("\n--- 第2步：录取分数线 ---")
        insertSchoolScore()
        print("\n--- 第3步：专业分数线 ---")
        getMajorScoreNear5Byhread("江西")
        print("\n--- 第4步：招生计划 ---")
        getCollegePlan()
        print("\n" + "=" * 50)
        print("全量爬取完成！")
        print("=" * 50)
    elif step in steps:
        print(f"执行步骤: {step}")
        steps[step]()
    else:
        print(f"未知步骤: {step}")
        print(f"可用步骤: {', '.join(steps.keys())}")


#学校清单
# schoolListUrl="https://gaokao.baidu.com/gk/gkschool/list?province=&city=&batch=&character=&type=&education=&nature=&needFilter=0&rn=10&"
schoolListUrl="https://gaokao.baidu.com/gk/gkschool/list?rn=10&"
#分数线
# 江西高考制度：2020-2023 旧高考(理科/文科)，2024起 新高考3+1+2(物理类/历史类)
# 根据年份自动选择 curriculum 参数
def get_curriculum_list(year):
    # 返回 (curriculum_display, curriculum_api_value) 列表
    if int(year) >= 2024:
        return [("物理类", "物理类"), ("历史类", "历史类")]
    else:
        return [("理科", "理科"), ("文科", "文科")]

schoolScoreUrl="https://gaokao.baidu.com/gk/gkschool/schoolscore?"
# 参数pn-页数，school-中文学校名，province-省，year-年份
schoolMajorScoreUrl="https://gaokao.baidu.com/gk/gkschool/majorscore?rn=10&subject=&sortType&version=2&needFilter=1&"
# 参数pn-第几条记录开始，query-中文学校名，province-省，year-年份,curriculum-课程类型,3+3综合,rn-每页记录数
schoolPlanUrl="https://gaokao.baidu.com/gk/gkschool/getrecruitingscheme?"

schoolFieldList=["\"college_name\"" ,"\"rankTypeShow\"" ,"rankType","rank",\
    "globalRank","\"uniqueRank\"","province","city","location",\
    "school_type","\"education\"","nature","batch","score_city",\
    "score_list","tag","logourl"]

schoolScoreFieldList=["\"legalName\"","province","year","curriculum",\
    "\"batchName\"","\"enrollType\"","\"minScore\"","\"minScoreOrder\"",\
    "\"minCha\"","\"enrollNum\""]

schoolMajorScoreFieldList=["\"legalName\"" ,"\"majorName\"","province","year",\
    "curriculum","\"batchName\"","tags","\"minScore\"","\"minScoreOrder\"",\
    "\"simpleMajorName\"","\"majorNameDesc\"","\"simplifySpecialCourse\"",\
    "\"specialCourse\"","\"majorGroup\""]

schoolPlanFieldList=["major_name","province",\
					 "curriculum","category","year",\
					 "batch_name","enroll_num","tuition","lengthOfSchooling","selectSubjects"]

def create_tables():
    """创建所有数据表（如不存在）"""
    dbconn = DBConn()
    ddl_statements = [
        '''CREATE TABLE IF NOT EXISTS college_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logourl TEXT, college_name TEXT, rankTypeShow TEXT,
            rankType TEXT, rank TEXT, globalRank TEXT, uniqueRank TEXT,
            province TEXT, city TEXT, location TEXT, school_type TEXT,
            education TEXT, nature TEXT, batch TEXT, score_city TEXT,
            score_list TEXT, tag TEXT, logo BLOB
        )''',
        '''CREATE TABLE IF NOT EXISTS college_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT, name TEXT, detail TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS schoolscore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, province TEXT, year TEXT, curriculum TEXT,
            batchName TEXT, enrollType TEXT, minScore TEXT,
            minScoreOrder TEXT, minCha TEXT, enrollNum TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS majorscore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, majorName TEXT, province TEXT, year TEXT,
            curriculum TEXT, batchName TEXT, tags TEXT, minScore TEXT,
            minScoreOrder TEXT, simpleMajorName TEXT, majorNameDesc TEXT,
            simplifySpecialCourse TEXT, specialCourse TEXT, majorGroup TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS college_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, major_name TEXT, province TEXT,
            curriculum TEXT, category TEXT, year TEXT, batch_name TEXT,
            enroll_num TEXT, tuition TEXT, lengthOfSchooling TEXT,
            selectSubjects TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS crawl_skip (
            school_name TEXT,
            year TEXT,
            curriculum TEXT,
            table_name TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (school_name, year, curriculum, table_name)
        )'''
    ]
    for sql in ddl_statements:
        dbconn.execSql(sql)
    print("数据库表创建/确认完成 ✓")


def is_skipped(school, year, curriculum, table):
    """查询 crawl_skip 表，确认该组合是否已确认无数据"""
    dbconn = DBConn()
    r = dbconn.execQuery(
        "SELECT 1 FROM crawl_skip WHERE school_name=? AND year=? AND curriculum=? AND table_name=?",
        (school, str(year), curriculum, table),
    )
    return len(r) > 0


def mark_skipped(school, year, curriculum, table):
    """记录该组合已确认无数据"""
    dbconn = DBConn()
    dbconn.execSql(
        "INSERT OR IGNORE INTO crawl_skip(school_name, year, curriculum, table_name) VALUES(?,?,?,?)",
        (school, str(year), curriculum, table),
    )


def create_unique_indexes():
    """为4张表创建唯一索引，支持增量更新"""
    create_tables()
    dbconn = DBConn()
    indexes = [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_college_info_name ON college_info(college_name)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_schoolscore_uniq ON schoolscore(legalName, province, year, curriculum, batchName, enrollType)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_majorscore_uniq ON majorscore(legalName, majorName, province, year, curriculum, batchName)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_college_plan_uniq ON college_plan(legalName, major_name, province, year, batch_name)"
    ]
    for sql in indexes:
        try:
            dbconn.execSql(sql)
        except Exception as e:
            print(f"创建索引警告: {e}")
    print("唯一索引创建完成 ✓")

# ======获取高校信息
def getSchoolList(pageno):
    url = schoolListUrl+"pn="+str(pageno)
    for attempt in range(3):
        try:
            response=requests.get(url, timeout=30)
            respJson=json.loads(response.text)
            return respJson["data"]["ranking"]["tRow"]
        except Exception as e:
            print(f"  获取第{pageno}页失败 (第{attempt+1}次): {e}")
            if attempt < 2:
                time.sleep(3)
    return None


# 允许参与动态查询的表/列（防注入）
_ALLOWED_TABLES = {
    "college_info", "schoolscore", "majorscore", "college_plan", "crawl_skip",
}
_ALLOWED_COLS = {
    "legalName", "province", "year", "curriculum", "batchName", "enrollType",
    "majorName", "major_name", "batch_name", "college_name", "school_name",
    "table_name",
}


def has_data(table, conditions):
    """检查数据库中是否已存在指定条件的记录，避免重复 API 请求（参数化）"""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"不允许的表名: {table}")
    cols, params = [], []
    for k, v in conditions.items():
        if k not in _ALLOWED_COLS:
            raise ValueError(f"不允许的列名: {k}")
        cols.append(f"{k}=?")
        params.append(v)
    where = " AND ".join(cols)
    sql = f"SELECT 1 FROM {table} WHERE {where} LIMIT 1"
    dbconn = DBConn()
    result = dbconn.execQuery(sql, params)
    return len(result) > 0


def _insert_dict(table, field_list, data, mode="ignore"):
    """参数化 INSERT：field_list 可含引号包装的字段名。"""
    if table not in _ALLOWED_TABLES and table != "college_info":
        # college_info 已在 allowed；保留显式
        pass
    cols, placeholders, params = [], [], []
    for num in field_list:
        fieldname = num.replace('"', "")
        if fieldname in data and data[fieldname] is not None:
            cols.append(fieldname)
            placeholders.append("?")
            params.append(str(data[fieldname]))
    if not cols:
        return
    verb = "INSERT OR IGNORE" if mode == "ignore" else "INSERT OR REPLACE"
    sql = f"{verb} INTO {table}({','.join(cols)}) VALUES({','.join(placeholders)})"
    dbconn = DBConn()
    dbconn.execSql(sql, params)


# 更新所有学校信息
def getAllSchool():
	# 先创建唯一索引，支持增量更新
	create_unique_indexes()

	# 从 API 获取真实总数，计算最大页数
	import json
	try:
		r = requests.get(schoolListUrl+"pn=1", timeout=15)
		total = json.loads(r.text)["data"]["pageInfo"]["total"]
	except:
		total = 3052
	# 计算最大页数：统一用 rn=10
	MAX_PAGE = math.ceil(total / 10)
	dbconn = DBConn()
	existing = dbconn.execQuery("select count(1) from college_info")
	existing_count = existing[0][0] if existing else 0
	pageno = (existing_count // 10) + 1
	count = existing_count

	if pageno > 1:
		print(f"数据库已有 {existing_count} 所，共 {total} 所，从第 {pageno}/{MAX_PAGE} 页继续...")

	while pageno <= MAX_PAGE:
		data=getSchoolList(pageno)
		if data is None or len(data)==0 :
			pageno += 1
			continue
		for key in range(len(data)):
			count=count+1
			insertSchool(data[key], skip_logo=True)

		print(f"第 {pageno}/{MAX_PAGE} 页 (已处理 {count}/{total} 所学校)")
		time.sleep(1)
		pageno=pageno+1

def deleteAllSchool():
	sqlstr="delete from college_info"
	dbconn=DBConn()
	dbconn.execSql(sqlstr)

def insertSchool(schoolInfo, skip_logo=False):
	row = {}
	for num in schoolFieldList:
		fieldname = num.replace('"', "")
		if fieldname == "logourl":
			row["logourl"] = str(schoolInfo.get("logo") or schoolInfo.get("logourl") or "")
		elif fieldname in schoolInfo:
			row[fieldname] = schoolInfo[fieldname]
	if "logourl" not in row:
		row["logourl"] = str(schoolInfo.get("logo") or "")

	content = None
	if not skip_logo:
		logoUrl = schoolInfo.get("logo")
		try:
			a = urlparse(logoUrl)
			filename = os.path.basename(a.path) or "logo.tmp"
			urllib.request.urlretrieve(logoUrl, filename=filename)
			with open(filename, "rb") as f:
				content = base64.b64encode(f.read())
			os.remove(filename)
		except Exception as e:
			print(f"  logo下载失败(跳过): {e}")
			content = None

	cols = list(row.keys())
	placeholders = ",".join(["?"] * len(cols))
	sql = f"INSERT OR REPLACE INTO college_info({','.join(cols)}) VALUES({placeholders})"
	DBConn().execSql(sql, [str(row[c]) for c in cols])

	if content:
		DBConn().execSql(
			"UPDATE college_info SET logo=? WHERE college_name=?",
			(content, schoolInfo["college_name"]),
		)

	print(schoolInfo["college_name"], "数据更新完成")
	
def getAllSchoolName():
	sqlstr="select college_name from college_info order by id"

	dbconn=DBConn()
	schools=dbconn.execQuery(sqlstr)

	return schools

	
# ===========================
# 录取分数线
def getScore(college_name, province, year, curriculum):
	try:
		url=schoolScoreUrl+"curriculum="+str(curriculum)+"&school="+str(college_name)+"&province="+str(province)+"&year="+str(year)
		print(url)
		response=requests.get(url, timeout=(10, 30))
		respText=response.text
		respJson=json.loads(respText)
		retJson=respJson["data"]["school_score"]["dataList"]
		return retJson
	except Exception as e:
		print(f"  {college_name} {year} {curriculum}: 跳过 ({e})")
		return None

def deleteAllSchoolScore():
	sqlstr="delete from schoolscore"
	dbconn=DBConn()
	dbconn.execSql(sqlstr)

# 获取学校分数线
def insertSchoolScore():
	# 创建唯一索引，支持增量更新
	create_unique_indexes()

	# 查询有哪些学校尚未入库 schoolscore（用 LEFT JOIN 找缺失）
	dbconn = DBConn()
	missing = dbconn.execQuery(
		"SELECT c.college_name FROM college_info c "
		"LEFT JOIN (SELECT DISTINCT legalName FROM schoolscore) s ON c.college_name = s.legalName "
		"LEFT JOIN (SELECT DISTINCT school_name FROM crawl_skip WHERE table_name='schoolscore') sk ON c.college_name = sk.school_name "
		"WHERE s.legalName IS NULL AND sk.school_name IS NULL "
		"ORDER BY c.id"
	)
	schoolNames = [(row[0],) for row in missing]
	
	if not schoolNames:
		print("schoolscore 数据已完整，无需补爬")
		return

	total_missing = len(schoolNames)
	print(f"schoolscore 还需爬取 {total_missing} 所学校")

	startTime=datetime.now()

	count=0
	school_idx=0
	for schoolName in schoolNames:
		school_idx+=1
		if school_idx % 10 == 0:
			print(f"[{school_idx}/{total_missing}] 当前: {schoolName[0]} (已入库 {count} 行)")
		year=2025
		while year>=2021 :
			# 江西每年分文理/物理历史两类，分别爬取
			for cur_label, cur_api in get_curriculum_list(str(year)):
				# 跳过已确认无数据的组合
				if is_skipped(schoolName[0], str(year), cur_api, "schoolscore"):
					continue
				schoolscores=getScore(schoolName[0],"江西",year,cur_api)
				if schoolscores==None :
					mark_skipped(schoolName[0], str(year), cur_api, "schoolscore")
					continue
				# print(schoolscores)
				for schoolscore in schoolscores:
					if schoolscore.get("year") == str(year):
						_insert_dict("schoolscore", schoolScoreFieldList, schoolscore, mode="ignore")
						count += 1
						if count % 100 == 0:
							print("已更新：", count)

			year=year-1
			time.sleep(0.1)
	endTime=datetime.now()
	print("已更新",count,"条高校录取分数线，耗时：",(endTime-startTime),"\n")

#================================================================
# 获取专业分数线
def getMajorScore(college_name, province, year, curriculum):
	# 跳过已确认无数据的组合
	if is_skipped(college_name, str(year), curriculum, "majorscore"):
		return
	# 跳过已入库的(学校,年份,类型)组合
	if has_data("majorscore", {"legalName": college_name, "province": province, "year": str(year), "curriculum": curriculum}):
		print(f"  跳过 {college_name} {year} {curriculum}")
		return

	url=schoolMajorScoreUrl+"curriculum="+str(curriculum)+"&school="+str(college_name)+"&province="+str(province)+"&year="+str(year)

	bFlag=True
	pn=1
	# delMajorScore(college_name,province)

	while bFlag :
		# 请求重试（最多3次）
		for retry in range(3):
			try:
				response=requests.get(url+"&pn="+str(pn), timeout=(10, 30))
				break
			except requests.exceptions.ReadTimeout:
				if retry < 2:
					print(f"  超时重试 {retry+1}/3: {college_name} {year} pn={pn}")
					time.sleep(5)
				else:
					print(f"  超时放弃: {college_name} {year} pn={pn}")
					bFlag=False
					break
		print(url+"&pn="+str(pn))
		pn=pn+1
		respText=response.text
		# print(respText)
		respJson=json.loads(respText)
		print(url)
		time.sleep(0.05)
		majorscores=None
		try:
			if respJson["errno"]!=0:
				break

			majorscores=respJson["data"]["major_score"]["dataList"]

		# print(majorscores)

			if len(majorscores)<=0 :
				mark_skipped(college_name, str(year), curriculum, "majorscore")
				bFlag=False
			else:
				if majorscores[0]["year"]!=str(year) :
					bFlag=False
				else:
					for majorscore in majorscores :
						insertMajorScore(majorscore)
						# print(majorscore)
					print(college_name,"-",province,"-",year,"-",curriculum,"-","查询成功！")
		except Exception as e:
			bFlag=False
			mark_skipped(college_name, str(year), curriculum, "majorscore")
			if 'dataList' not in str(e):
				print(college_name,"-",province,"-",year,"-",f"查询出错: {e}")
			
def delMajorScore(college_name, province):
	DBConn().execSql(
		"DELETE FROM majorscore WHERE legalName=? AND province=?",
		(college_name, province),
	)


def delAllMajorScore():
	DBConn().execSql("DELETE FROM majorscore")


def insertMajorScore(majorscore):
	_insert_dict("majorscore", schoolMajorScoreFieldList, majorscore, mode="ignore")
	
#近5年的专业成绩，按年份和文理分类分别爬取
def getMajorScoreNear5(college_name, province):
	year=2025
	while year>=2021:
		for cur_label, cur_api in get_curriculum_list(str(year)):
			getMajorScore(college_name, province, str(year), cur_api)
		year=year-1
		time.sleep(0.1)

def getMajorScoreNear5s(college_names,province,threadno):

	for college_name in college_names:
		print("线程",threadno,college_name,province)
		getMajorScoreNear5(college_name,province)

# 大学名字、省份、线程数
def getMajorScoreNear5Byhread(province, threadnum=1):
	# 创建唯一索引，支持增量更新
	create_unique_indexes()

	# 查询有哪些学校尚未入库 majorscore
	dbconn = DBConn()
	missing = dbconn.execQuery(
		"SELECT c.college_name FROM college_info c "
		"INNER JOIN (SELECT DISTINCT legalName FROM schoolscore) sc ON c.college_name = sc.legalName "
		"LEFT JOIN (SELECT DISTINCT legalName FROM majorscore) s ON c.college_name = s.legalName "
		"LEFT JOIN (SELECT DISTINCT school_name FROM crawl_skip WHERE table_name='majorscore') sk ON c.college_name = sk.school_name "
		"WHERE s.legalName IS NULL AND sk.school_name IS NULL ORDER BY c.id"
	)
	schoolNames = [row[0] for row in missing]
	
	if not schoolNames:
		print("majorscore 数据已完整，无需补爬")
		return
	
	total_missing = len(schoolNames)
	print(f"majorscore 还需爬取 {total_missing} 所学校")

	schoolNameList=[]
	i=0
	while i<threadnum:
		schoolNameList.append([])
		i=i+1
	threadingList=[]

	index=0
	count=len(schoolNames)
	for schoolName in schoolNames:
		schoolNameList[index % threadnum].append(schoolName)
		index=index+1


	i=0
	while i<threadnum:
		threadingList.append(threading.Thread(target=getMajorScoreNear5s,args=(schoolNameList[i],province,i)))
		print(schoolNameList[i])
		i=i+1

	#启动线程
	i=0
	while i<threadnum:
		threadingList[i].start()
		i=i+1

	#等待所有线程完成
	for t in threadingList:
		t.join()
	print("所有线程执行完毕！")

#================================================================
# 获取学校招生计划
def getCollegePlanFromUrl(school, province, year, curriculum, pn, rn):
	# 参数pn-第几条记录开始，query-中文学校名，province-省，year-年份,curriculum-课程类型,rn-每页记录数
	
	url=schoolPlanUrl+"curriculum="+str(curriculum)+"&query="+school+"&province="+province+"&year="+str(year)+"&pn="+str(pn)+"&rn="+str(rn)
	for attempt in range(3):
		try:
			response=requests.get(url, timeout=(10, 30))
			respJson=json.loads(response.text)
			if respJson.get("errno") != 0:
				return None
			ret=respJson["data"]["list"]
			return ret
		except requests.exceptions.ReadTimeout:
			if attempt < 2:
				print(f"  超时重试 {attempt+1}/3: {school} {year}")
				time.sleep(3)
			else:
				print(f"  超时放弃: {school} {year}")
				return None
		except Exception as e:
			if attempt < 2:
				time.sleep(1)
			else:
				print(f"招生计划获取失败: {e}")
				print(url)
				return None
	

# 插入招生计划数据库
def insertCollegePlan(collegePlan, schoolName):
	row = dict(collegePlan)
	row["legalName"] = schoolName
	fields = ['"legalName"'] + schoolPlanFieldList
	_insert_dict("college_plan", fields, row, mode="ignore")
	
def getCollegePlan():
	# 创建唯一索引，支持增量更新
	create_unique_indexes()

	# 查询有哪些学校尚未入库 college_plan
	dbconn = DBConn()
	missing = dbconn.execQuery(
		"SELECT c.college_name FROM college_info c "
		"LEFT JOIN (SELECT DISTINCT legalName FROM college_plan) s ON c.college_name = s.legalName "
		"LEFT JOIN (SELECT DISTINCT school_name FROM crawl_skip WHERE table_name='college_plan') sk ON c.college_name = sk.school_name "
		"WHERE s.legalName IS NULL AND sk.school_name IS NULL ORDER BY c.id"
	)
	schoolNames = missing
	
	if not schoolNames:
		print("college_plan 数据已完整，无需补爬")
		return
	
	total_missing = len(schoolNames)
	print(f"college_plan 还需爬取 {total_missing} 所学校")
	
	for idx, schoolName in enumerate(schoolNames, 1):
		if idx % 50 == 0 or idx == 1:
			print(f"[{idx}/{total_missing}] 当前: {schoolName[0]}")
		province="江西"
		year=2026
		while year>=2021 :
			# 江西每年分文理/物理历史两类，分别爬取
			for cur_label, cur_api in get_curriculum_list(str(year)):
				# 跳过已确认无数据的组合
				if is_skipped(schoolName[0], str(year), cur_api, "college_plan"):
					continue
				# 跳过已有数据的组合
				if has_data("college_plan", {"legalName": schoolName[0], "province": province, "year": str(year), "curriculum": cur_api}):
					continue
				rn=50
				pn=0
				flag=True
				while flag :
					collegePlans=getCollegePlanFromUrl(schoolName[0], province, year, cur_api, pn, rn)
					if collegePlans==None or len(collegePlans)<=0 :
						mark_skipped(schoolName[0], str(year), cur_api, "college_plan")
						flag=False
					else:
						for collegePlan in collegePlans :
							# print(collegePlan)
							insertCollegePlan(collegePlan,schoolName[0])
						print(schoolName[0],"-",province,"-",year,"-",cur_label,"-","查询成功！")
						pn=pn+rn
			year=year-1
			time.sleep(0.1)
		

# insertSchoolScore()
# getAllSchool()
# print(getSchoolList(1))
# 取消注释 getMajorScoreNear5Byhread("江西")
# 单校测试：抓取南昌大学2024年物理类/历史类专业分数线

if __name__ == "__main__":
    main()