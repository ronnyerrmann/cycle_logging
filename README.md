# cycle_logging
App to log daily exercise and and to analyse the data.

One could just keep using a spreadsheet, or alternatively practise to use some other tools: MySQL, Python, Java, PHP, Javascript, Django, ...

### Create the database
As root:
```
sudo mysql -u root
```
Run: (CREATE, ALTER, REFERENCES, INDEX only necessary when using Django later)
```
CREATE USER fahrrad@localhost IDENTIFIED BY 'good_password';
CREATE DATABASE fahrrad;
GRANT INSERT, UPDATE, DELETE, SELECT on fahrrad.* TO fahrrad@localhost;
GRANT CREATE, ALTER, REFERENCES, INDEX on fahrrad.* TO fahrrad@localhost;
GRANT SELECT, LOCK TABLES ON fahrrad.* TO fahrrad@localhost;
FLUSH PRIVILEGES;
USE fahrrad;
CREATE TABLE fahrrad_rides (EntryID mediumint NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Date date NOT NULL,
    DayKM float(10,3) NOT NULL,
    DaySeconds mediumint NOT NULL,
    DayKMH float(10,4),
    TotalKM float NOT NULL,
    TotalSeconds int NOT NULL,
    TotalKMH float(10,4),
    CulmKM float,
    CulmSeconds int,
    wasupdated bool DEFAULT true,
    UNIQUE (TotalKM),
    CONSTRAINT UC_daily UNIQUE (Date, DayKM, DaySeconds) );
COMMIT;
```

As user `fahrrad`:
```
mysql -u fahrrad -p
```
Run an example insert and select: 
```
USE fahrrad;
INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds)
            VALUES ('2021-12-20', 19.14, 43*60+39, 90796, 3968*3600+26);
COMMIT;
SELECT * FROM fahrrad_rides;
```

More MySQL settings (e.g. fill in missing values, create summarising tables) are described in file [MySQL_scheduler.md](MySQL_scheduler.md)

### Create settings file to use for programs:
Create a file `fahrrad_mysql.params` with entries:
```
host = localhost
user = fahrrad
password = good_password
db = fahrrad
```

### Import old values from a csv file
Either tab or comma separated. The convertion between csv columns to database columns is defined in parameter **entries_for_mysql** in **import_csv_mysql.py**
```
python3 import_csv_mysql.py <csv_file.csv>
```

### Add daily values
#### Compile and run (Linux)
(classpath might not necessary, need if *java.lang.ClassNotFoundException: com.mysql.cj.jdbc.Drive*. The package can be downloaded from https://dev.mysql.com/downloads/connector/j/ )
```
javac -d . StringModifications.java && javac -d . ConnectionMYSQL.java && java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. Fahrrad.java
```

Todo: Here I want to add checks to the input data to check it's consistent with existing values and add a GUI later.

### Show results in a Webbrowser, using clasic methods:
Open `cycle.php` in your webserver (php needs to be activated). The folder `node_modules` needs to be copied to be located in the same path as `cycle.php`. When the search is performed, the file will call itself. The [settings file](#create-settings-file-to-use-for-programs) needs to be one level above the document root directory (e.g. */var/www/*) or **$mysqlsettingsfile** needs to be changed in the fist few lines of `cycle.php`.

#### Copy all neccessary files:
```
cd <this/git/folder>
cp -pr cycle.css cycle.js cycle.php favicon.ico node_modules   <path/to/webserver/folder>
```

#### Install the javascript dependencies manually:
To use the most actual java script files, instead of copying the folder `node_modules` it can be created manually, using for example using **npm**. First npm is initiated in the current folder and then the required packages are installed:
```
cd <path/to/webserver/folder>
npm init --y
npm install chart.js jquery.min.js chartjs-plugin-zoom
```

#### Running example:
The website runs on a test server. Feel free to give it a try: [Cycle Results (PHP/Javascript)](http://ronnyerrmann.ddns.net:80).

### Show results in a Webbrowser, using Django:
To install Django you can follow: [https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/development_environment]

The following packages are required
```
pip install requests urllib3 django pandas plotly
```

Allow access to the database used by Django tests (as given in settings.py for `DATABASES[default][TEST][NAME]`:
```commandline
sudo mysql -u root
```
```
GRANT ALL PRIVILEGES ON cycle_test.* TO 'fahrrad'@'localhost';
```
The tests can be executed by running in folder `cycle_logging/cycle_django`:
```commandline
python manage.py test
```

The website runs on a test server: [Cycle Results (Django)](http://ronnyerrmann.ddns.net:8000).

### Learnings
* Be more consistent with your names: instead of using "MonthKM" or "YearDays" for the front end it is easier to use the same column names for each table.
* When crating the weekly, monthly, or yearly summary tables links between the tables could be created, to allow easier movement in the front end.

### Final notes:
If you tried some or all of the scripts, let me know how it went: Ronny Errmann: ronny.errmann@gmail.com

