download news from ssdut.dlut.edu.cn an format it
##大连理工大学软件学院学院新闻抓取、格式化服务。
### http://115.28.2.165:8000/


本项目是对SSdut-News工具的拓展、完善。

SSdut-News: https://github.com/dawn110110/SSdut-News

##尚未完成

##试用

1. 安装依赖：`pip install -r requirements.txt`，如果使用MySQL，要安装驱动，`pip install MySQL-python`
2. 数据库设置，打开`config.py`，例如：

    db_config = 'mysql://user:pass@hostname/dbname'

3. 建表`python install.py`
4. 抓取新闻`python crawler.py`，等待片刻抓取结束。未来这个进程会自动更新新闻，现在只是抓取一次。
5. 跑起tornado server：`python server.py`
6. 访问`http://localhost:8000`
7. 尝试url如下：
    - `/id/2000`
    - `/id/2000-2003`
    - `/date/2013-1-1/2013-3-2`
    - `/date/2013-3-1`
    - `/search/教务处`

以上url除搜索外，均返回json格式结果，编码unicode，搜索的结果大致如下：
![image](static/example.png)

