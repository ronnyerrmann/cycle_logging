Login as root

```
sudo mysql -u root
USE fahrrad;
```

Enable the Scheduler
```
SET GLOBAL event_scheduler = ON;
```

Add the summarise tables and global variables
```
CREATE TABLE fahrrad_weekly_summary (Week_starting_on DATE NOT NULL PRIMARY KEY,
    WeekKM FLOAT(10,3) NOT NULL,
    WeekSeconds MEDIUMINT NOT NULL,
    WeekKMH FLOAT(10,4),
    WeekDays TINYINT NOT NULL );
    
CREATE TABLE fahrrad_monthly_summary (Month_starting_on DATE NOT NULL PRIMARY KEY,
    MonthKM FLOAT(10,3) NOT NULL,
    MonthSeconds MEDIUMINT NOT NULL,
    MonthKMH FLOAT(10,4),
    MonthDays TINYINT NOT NULL );
    
CREATE TABLE fahrrad_yearly_summary (Year_starting_on DATE NOT NULL PRIMARY KEY,
    YearKM FLOAT(10,3) NOT NULL,
    YearSeconds MEDIUMINT NOT NULL,
    YearKMH FLOAT(10,4),
    YearDays MEDIUMINT  NOT NULL);
```

Create a trigger to calculate the missing values before inserting or modifying.
The helper table tracks the dates that were changed, so only the necessary summary table is updated.
(Note to myself: @var only exists in a session, so if it is changed by a trigger, an event wouldn't know about it.)
More conditions could be checked, as only if Date, DayKM, or DaySeconds change, the summary tables or culminated values need to be re-calculated.
```
CREATE TABLE helper(min_date DATE, max_date DATE);
INSERT INTO helper VALUES(NULL, NULL);

DELIMITER $$

DROP PROCEDURE IF EXISTS check_date$$
CREATE PROCEDURE check_date(new_date DATE)
BEGIN
    SET @min_date := (SELECT min_date FROM helper);
    IF @min_date IS NULL THEN
        SET @min_date := new_date;
        SET @max_date := new_date;
    ELSE
        SET @max_date := (SELECT max_date FROM helper);
        SET @min_date := IF(new_date < @min_date, new_date, @min_date);
        SET @max_date := IF(new_date > @max_date, new_date, @max_date);
    END IF;
    UPDATE helper SET min_date = @min_date, max_date = @max_date;
END$$

DROP TRIGGER IF EXISTS before_fahrrad_rides_insert$$
CREATE TRIGGER before_fahrrad_rides_insert
    BEFORE INSERT
    ON fahrrad_rides FOR EACH ROW
    BEGIN
        SET NEW.DayKMH = NEW.DayKM/NEW.DaySeconds*3600;
        SET NEW.TotalKMH =  NEW.TotalKM/NEW.TotalSeconds*3600;
        CALL check_date(NEW.Date);
    END$$
    
DROP TRIGGER IF EXISTS before_fahrrad_rides_modification$$
CREATE TRIGGER before_fahrrad_rides_modification
    BEFORE UPDATE 
    ON fahrrad_rides FOR EACH ROW
    BEGIN
        SET NEW.DayKMH = NEW.DayKM/NEW.DaySeconds*3600;
        SET NEW.TotalKMH =  NEW.TotalKM/NEW.TotalSeconds*3600;
        CALL check_date(NEW.Date);
        CALL check_date(OLD.Date);
    END$$

DROP TRIGGER IF EXISTS before_fahrrad_rides_deletion$$
CREATE TRIGGER before_fahrrad_rides_deletion
    BEFORE DELETE 
    ON fahrrad_rides FOR EACH ROW
    BEGIN
        CALL check_date(OLD.Date);
    END$$

DROP TRIGGER IF EXISTS before_weekly_summary_insert$$
CREATE TRIGGER before_weekly_summary_insert
    BEFORE INSERT
    ON fahrrad_weekly_summary FOR EACH ROW
        SET NEW.WeekKMH = NEW.WeekKM/NEW.WeekSeconds*3600$$

DROP TRIGGER IF EXISTS before_monthly_summary_insert$$
CREATE TRIGGER before_monthly_summary_insert
    BEFORE INSERT
    ON fahrrad_monthly_summary FOR EACH ROW
        SET NEW.MonthKMH = NEW.MonthKM/NEW.MonthSeconds*3600$$

DROP TRIGGER IF EXISTS before_yearly_summary_insert$$
CREATE TRIGGER before_yearly_summary_insert
    BEFORE INSERT
    ON fahrrad_yearly_summary FOR EACH ROW
        SET NEW.YearKMH = NEW.YearKM/NEW.YearSeconds*3600$$

DELIMITER ;
```

Summarize the data (if there were updates) and calculate the culmulative values.
Only check it once a minute.
```
DELIMITER $$

DROP FUNCTION IF EXISTS fn_get_CulmKM$$
CREATE FUNCTION `fn_get_CulmKM`(_Date DATE) RETURNS FLOAT
    READS SQL DATA
    BEGIN
        DECLARE r FLOAT;
        SELECT SUM(DayKM) INTO r FROM fahrrad_rides WHERE Date <= _Date;
        RETURN r;
    END $$

DROP FUNCTION IF EXISTS fn_get_CulmSeconds$$
CREATE FUNCTION `fn_get_CulmSeconds`(_Date DATE) RETURNS INT
    READS SQL DATA
    BEGIN
        DECLARE r INT;
        SELECT SUM(DaySeconds) INTO r FROM fahrrad_rides WHERE Date <= _Date;
        RETURN r;
    END $$

DROP PROCEDURE IF EXISTS proc_summarise$$
CREATE PROCEDURE proc_summarise()
BEGIN
    DECLARE number_years INT DEFAULT 0;
    DECLARE number_months INT DEFAULT 0;
    -- DECLARE number_weeks INT DEFAULT 0;
    DECLARE ii INT DEFAULT 0;
    DECLARE jj INT DEFAULT 0;
    DECLARE This_year INT DEFAULT 0;
    DECLARE This_month INT DEFAULT 0;
    DECLARE This_date DATE DEFAULT '2000-01-01';
    DECLARE End_date DATE DEFAULT '2000-01-01';
    DECLARE Max_date DATE DEFAULT '2000-01-01';
    DECLARE This_day INT DEFAULT 0;
    DECLARE ThisKM FLOAT DEFAULT 0;
    DECLARE ThisSeconds INT DEFAULT 0;
    DECLARE ThisDays INT DEFAULT 0;
    -- get the years with new data
    SET @min_date := (SELECT min_date FROM helper);
    SET @max_date := (SELECT max_date FROM helper);
    SELECT COUNT(DISTINCT YEAR(Date)) INTO number_years FROM fahrrad_rides WHERE Date >= @min_date AND Date <= @max_date;
    SET ii = 0;
    WHILE ii < number_years DO
        -- get the current year as int
        SELECT DISTINCT YEAR(Date) INTO This_year FROM fahrrad_rides WHERE wasupdated=1 LIMIT ii,1;
        SELECT SUM(DayKM), SUM(DaySeconds) INTO ThisKM, ThisSeconds FROM fahrrad_rides WHERE YEAR(Date) = This_year;
        SELECT COUNT(wasupdated) INTO ThisDays FROM fahrrad_rides WHERE YEAR(Date) = This_year;
        DELETE FROM fahrrad_yearly_summary WHERE Year_starting_on = CONCAT(This_year,'-01-01');
        INSERT INTO fahrrad_yearly_summary (Year_starting_on, YearKM, YearSeconds, YearDays) 
            VALUES (CONCAT(This_year,'-01-01'), ThisKM, ThisSeconds, ThisDays);
        -- get the months within the year with new data
        SELECT COUNT(DISTINCT MONTH(Date)) INTO number_months FROM fahrrad_rides WHERE wasupdated=1 AND YEAR(Date) = This_year;
        SET jj = 0;
        WHILE jj < number_months DO
            -- get the current month as int
            SELECT DISTINCT MONTH(Date) INTO This_month FROM fahrrad_rides WHERE wasupdated=1 AND YEAR(Date) = This_year LIMIT jj,1;
            SELECT SUM(DayKM), SUM(DaySeconds) INTO ThisKM, ThisSeconds FROM fahrrad_rides WHERE YEAR(Date) = This_year AND MONTH(Date) = This_month;
            SELECT COUNT(wasupdated) INTO ThisDays FROM fahrrad_rides WHERE YEAR(Date) = This_year AND MONTH(Date) = This_month;
            DELETE FROM fahrrad_monthly_summary WHERE Month_starting_on = CONCAT(This_year,'-',This_month,'-01');
            INSERT INTO fahrrad_monthly_summary (Month_starting_on, MonthKM, MonthSeconds, MonthDays) 
                VALUES (CONCAT(This_year,'-',This_month,'-01'), ThisKM, ThisSeconds, ThisDays);
            SET jj = jj+1;
        END WHILE;
        SET ii = ii+1;
    END WHILE;
    -- get the weeks with updates
    -- WEEK(Date) could be used, but then weeks 1 and 53 (of prev year) need to be combined
    -- SET number_weeks = CEIL(DATEDIFF(SELECT MAX(Date) FROM fahrrad_rides WHERE wasupdated=1, SELECT MIN(Date) FROM fahrrad_rides WHERE wasupdated=1)/7) + 2;7
    SELECT MAX(Date) INTO Max_date FROM fahrrad_rides WHERE wasupdated=1;
    SET Max_date = ADDDATE(Max_date, INTERVAL 7 DAY); 
    -- Find the first Monday
    SELECT MIN(Date) INTO This_date FROM fahrrad_rides WHERE wasupdated=1;
    SET This_day = WEEKDAY(This_date);
    SET This_date = SUBDATE(This_date, INTERVAL This_day DAY); 
    WHILE This_date < Max_date DO
        SET End_date = ADDDATE(This_date, INTERVAL 6 DAY);
        SELECT COUNT(wasupdated) INTO ThisDays FROM fahrrad_rides WHERE Date BETWEEN This_date AND End_date;
        IF ThisDays > 0 THEN
            SELECT SUM(DayKM), SUM(DaySeconds) INTO ThisKM, ThisSeconds FROM fahrrad_rides WHERE Date BETWEEN This_date AND End_date;
            DELETE FROM fahrrad_weekly_summary WHERE Week_starting_on = This_date;
            INSERT INTO fahrrad_weekly_summary (Week_starting_on, WeekKM, WeekSeconds, WeekDays) 
                VALUES (This_date, ThisKM, ThisSeconds, ThisDays);
        END IF;
        SET This_date = ADDDATE(This_date, INTERVAL 7 DAY); 
    END WHILE;
    -- not run the procedure again on the same data
    UPDATE helper SET min_date = NULL, max_date = NULL;
END$$

DROP EVENT IF EXISTS Summarize$$
CREATE EVENT Summarize
    ON SCHEDULE EVERY 1 MINUTE
    DO BEGIN
        SET @min_date := (SELECT min_date FROM helper);
        IF @min_date IS NOT NULL THEN
            UPDATE fahrrad_rides SET CulmKM = fn_get_CulmKM(Date) WHERE Date >= @min_date;
            UPDATE fahrrad_rides SET CulmSeconds = fn_get_CulmSeconds(Date) WHERE Date >= @min_date;
            CALL proc_summarise();
        END IF;
    END$$

DELIMITER ;
```