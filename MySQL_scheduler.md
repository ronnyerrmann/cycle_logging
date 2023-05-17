Login as root

```
sudo mysql -u root
USE fahrrad;
```

Enable the Scheduler
```
SET GLOBAL event_scheduler = ON;
```

Create a trigger to calculate the missing values before inserting or modifying:
```
DELIMITER $$

CREATE TRIGGER before_fahrrad_rides_insert
    BEFORE INSERT
    ON fahrrad_rides FOR EACH ROW
    BEGIN
        IF NEW.DayKMH IS NULL THEN
            SET NEW.DayKMH = NEW.DayKM/NEW.DaySeconds*3600;
        END IF;
        IF NEW.TotalKMH IS NULL THEN
            SET NEW.TotalKMH =  NEW.TotalKM/NEW.TotalSeconds*3600;
        END IF;
        IF NEW.CulmKM IS NULL THEN
            SET NEW.CulmKM = (SELECT SUM(DayKM) FROM fahrrad_rides WHERE Date <= NEW.Date) + NEW.DayKM;
        END IF;
        IF NEW.CulmSeconds IS NULL THEN
            SET NEW.CulmSeconds = (SELECT SUM(DaySeconds) FROM fahrrad_rides WHERE Date <= NEW.Date) + NEW.DaySeconds;
        END IF;
        SET NEW.wasupdated = 1;
    END$$
    
CREATE TRIGGER before_fahrrad_rides_modification
    BEFORE UPDATE 
    ON fahrrad_rides FOR EACH ROW
    BEGIN
        SET NEW.DayKMH = NEW.DayKM/NEW.DaySeconds*3600;
        SET NEW.TotalKMH =  NEW.TotalKM/NEW.TotalSeconds*3600;
        -- the next line won't update all future 
        SET NEW.CulmKM = (SELECT SUM(DayKM) FROM fahrrad_rides WHERE Date <= NEW.Date) + NEW.DayKM;
        SET NEW.CulmSeconds = (SELECT SUM(DaySeconds) FROM fahrrad_rides WHERE Date <= NEW.Date) + NEW.DaySeconds;
        SET NEW.wasupdated = 1;
    END$$

DELIMITER ;
```
Some things to note:
- if the date was given wrongly, after modifying it the summaries below will still contain the wrong data (a fix could be to also have an `to_update` column, which is set by the above triggers)
- if data is deleted, the same problem will occur
- the solution would be to set a modification bit in the summary tables for the old and new date

Create Summarised data:
```
USE fahrrad;
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
    
DELIMITER $$

CREATE TRIGGER before_weekly_summary_insert
    BEFORE INSERT
    ON fahrrad_weekly_summary FOR EACH ROW
    BEGIN
        IF NEW.WeekKMH IS NULL THEN
            SET NEW.WeekKMH = NEW.WeekKM/NEW.WeekSeconds*3600;
        END IF;
    END$$

CREATE TRIGGER before_monthly_summary_insert
    BEFORE INSERT
    ON fahrrad_monthly_summary FOR EACH ROW
    BEGIN
        IF NEW.MonthKMH IS NULL THEN
            SET NEW.MonthKMH = NEW.MonthKM/NEW.MonthSeconds*3600;
        END IF;
    END$$

CREATE TRIGGER before_yearly_summary_insert
    BEFORE INSERT
    ON fahrrad_yearly_summary FOR EACH ROW
    BEGIN
        IF NEW.YearKMH IS NULL THEN
            SET NEW.YearKMH = NEW.YearKM/NEW.YearSeconds*3600;
        END IF;
    END$$

DELIMITER ;

COMMIT;
```

Summarize the data (if there were updates):
```
DELIMITER $$

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
    SELECT COUNT(DISTINCT YEAR(Date)) INTO number_years FROM fahrrad_rides WHERE wasupdated=1;
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
    UPDATE fahrrad_rides SET wasupdated=0 WHERE wasupdated=1;
END;
$$

DROP EVENT IF EXISTS Summarize$$
CREATE EVENT Summarize
    ON SCHEDULE EVERY 1 MINUTE
    DO BEGIN
        IF (SELECT COUNT(wasupdated) FROM fahrrad_rides WHERE wasupdated=1) > 0 THEN
            -- GROUP BY could be used, but then can't count the entries for that
            CALL proc_summarise();
        END IF;
    END$$

DELIMITER ;
```

Update the main table in case values where added before the trigger `before_fahrrad_rides_insert` was created. Only do it daily and only on the coloumns necessary. Functions are necessary to create a sum up to a date.
```
DELIMITER $$

CREATE FUNCTION `fn_get_CulmKM`(_Date DATE) RETURNS FLOAT
    READS SQL DATA
    BEGIN
        DECLARE r FLOAT;
        SELECT SUM(DayKM) INTO r FROM fahrrad_rides WHERE Date <= _Date;
        RETURN r;
    END $$

CREATE FUNCTION `fn_get_CulmSeconds`(_Date DATE) RETURNS INT
    READS SQL DATA
    BEGIN
        DECLARE r INT;
        SELECT SUM(DaySeconds) INTO r FROM fahrrad_rides WHERE Date <= _Date;
        RETURN r;
    END $$

CREATE EVENT No_trigger_fahrrad_rides_insert
    ON SCHEDULE EVERY 1 DAY
    DO BEGIN
        -- Once a day make sure that summarized data is correct, this also updates all Culm* data
        UPDATE fahrrad_rides SET wasupdated = 1;
        -- Not necessary anymore as done when fahrrad_rides are updated
        -- UPDATE fahrrad_rides SET CulmKM = fn_get_CulmKM(Date) WHERE CulmKM IS NULL;
        -- UPDATE fahrrad_rides SET CulmSeconds = fn_get_CulmSeconds(Date) WHERE CulmSeconds IS NULL;
    END$$

DELIMITER ;
```
