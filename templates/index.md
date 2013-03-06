#SSDUT_NEWS_SERVER

##抓取 + 格式化 软件学院学生周知

如果你正在编写软院学生周知客户端，那么现在不必在客户端解析学院网的页面了，本站将解析好的，以json格式格式化好的学院新闻提供给你！

[报BUG / 源码](https://github.com/dawn110110/ssdut_news_server)

联系：dawn110110 at gmail dot com
##特性
- [开源](https://github.com/dawn110110/ssdut_news_server)
- 新闻各部分分离（标题、链接、来源、正文、正文原文（html）、发表人……），并以json格式提供给你
- 可按照 ID/ID范围/日期/日期范围 查询新闻
- 关键字搜索
- 查询最新新闻
- Unicode编码
- HTTP协议

##快速开始（以js为例）

获取最新一条新闻的信息（标题、链接、id、sha1、日期等）

	> var res = "";
	> $.get("/latest", function(r){ res = r; })
	> var latest = JSON.parse(res)
	
	> latest.title
	  "关于数字媒体技术系系标征集的通知"
	> latest.link
	  "/index.php/News/10098.html"
	> latest.sha1
	  "12e5a57b7448bde9f41f287526d9d8b8978011f5"
	> latest.date
	  "2013-03-03"
	> latest.id
	  2683

##支持的全部查询
以下查询均使用HTTP GET方法，返回结果均为JSON字符串，以下按照 url, 含义 列出。

- /latest
	- 获取最新一条消息的基本信息
- /id/2000 
	- 获取id为2000的一条消息
- /id/2000-2003 
	- 获取id为2000-2003之间的四条消息
- /date/2013-3-2 
	- 获取3月2日发布的所有消息
- /date/2013-1-1/2013-3-2 
	- 获取1月1日到3月2日之间的所有消息
- /search/日语 
	- 搜索包含关键字“日语”的所有新闻
- /search/日语%20演讲 
	- 搜索包含关键字“日语”和“演讲”的全部消息，支持更多关键字

除latest外，返回结果中每一条新闻均包括下列内容：

- id
- title
- body 新闻的内容html原文（仅内容部分）
- clean_body 新闻内容的纯文字部分（包含换行，缩进等。目前此项存在小bug若干，可能有无关内容）
- link 原文链接
- source 来源
- source_link 来源链接
- date 日期
- publisher 发表人
- sha1 原页面的sha1 hash值
