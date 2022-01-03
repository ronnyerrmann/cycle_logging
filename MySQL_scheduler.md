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

CREATE TRIGGER after_main_table_insert
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
        SET NEW.CulmKM = (SELECT SUM(DayKM) FROM fahrrad_rides WHERE Date < NEW.Date);
    END IF;
    IF NEW.CulmSeconds IS NULL THEN
        SET NEW.CulmSeconds = (SELECT SUM(DaySeconds) FROM fahrrad_rides WHERE Date < NEW.Date);
    END IF;
END$$

DELIMITER ;
```

Just an idea for next step:
```
CREATE EVENT Summarize
ON SCHEDULE EVERY 1 HOUR
DO
  INSERT INTO tbl_Students 
  VALUES (1,'Anvesh');
```

