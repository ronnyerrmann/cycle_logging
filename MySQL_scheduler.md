Login as root

```
sudo mysql -u root
```

Enable the Scheduler
```
SET GLOBAL event_scheduler = ON;
```

Create a trigger to calculate the mising values before inserting:
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
    END$$

DELIMITER ;
```

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

Summarize the data (if there were updates): - done for years, not yet done for months and weeks
```
DELIMITER $$

DROP PROCEDURE IF EXISTS proc_summarise$$
CREATE PROCEDURE proc_summarise()
BEGIN
    DECLARE number_years INT DEFAULT 0;
    DECLARE ii INT DEFAULT 0;
    DECLARE This_year INT DEFAULT 0;
    DECLARE YearKM FLOAT DEFAULT 0;
    DECLARE YearSeconds INT DEFAULT 0;
    DECLARE YearDays INT DEFAULT 0;
    SELECT COUNT(DISTINCT YEAR(Date)) INTO number_years FROM fahrrad_rides WHERE wasupdated=1;
    SET ii = 0;
    WHILE ii < number_years DO
        SELECT DISTINCT YEAR(Date) INTO This_year FROM fahrrad_rides WHERE wasupdated=1 LIMIT ii,1;
        SELECT SUM(DayKM), SUM(DaySeconds) INTO YearKM, YearSeconds FROM fahrrad_rides WHERE YEAR(Date) = This_year;
        SELECT COUNT(wasupdated) INTO YearDays FROM fahrrad_rides WHERE YEAR(Date) = This_year;
        DELETE FROM fahrrad_yearly_summary WHERE Year_starting_on = CONCAT(This_year,'-01-01');
        INSERT INTO fahrrad_yearly_summary (Year_starting_on, YearKM, YearSeconds, YearDays) 
            VALUES (CONCAT(This_year,'-01-01'), YearKM, YearSeconds, YearDays);
        SET ii = ii+1;
    END WHILE;
    UPDATE fahrrad_rides SET wasupdated=0 WHERE wasupdated=1;
END;
$$

DROP EVENT IF EXISTS Summarize$$
CREATE EVENT Summarize
    ON SCHEDULE EVERY 1 MINUTE
    DO BEGIN
        IF (SELECT COUNT(wasupdated) FROM fahrrad_rides WHERE wasupdated=1) > 0 THEN
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
        UPDATE fahrrad_rides SET DayKMH = DayKM/DaySeconds*3600 WHERE DayKMH IS NULL;
        UPDATE fahrrad_rides SET TotalKMH = TotalKM/TotalSeconds*3600 WHERE TotalKMH IS NULL;
        UPDATE fahrrad_rides SET CulmKM = fn_get_CulmKM(Date) WHERE CulmKM IS NULL;
        UPDATE fahrrad_rides SET CulmSeconds = fn_get_CulmSeconds(Date) WHERE CulmSeconds IS NULL;
    END$$

DELIMITER ;
```

