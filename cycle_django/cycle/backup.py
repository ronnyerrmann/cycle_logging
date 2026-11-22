import datetime
import glob
import gzip
import json
import os
import time
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import connection, transaction
from django.db.utils import IntegrityError, OperationalError

import cycle.models
from my_base import Logging, create_folder_if_required

BACKUP_FOLDER = "backup_database"

logger = Logging.setup_logger(__name__)


class Backup:
    file_changed_last_loaded = {}
    warn_db_dump_not_found = ["No database dump found"]

    def __init__(self):
        create_folder_if_required(BACKUP_FOLDER)
        super().__init__()

    @staticmethod
    def remove_old_files(data_name):
        files = glob.glob(os.path.join(BACKUP_FOLDER, data_name + "_*.csv.gz"))
        files.sort()

        keep_files = set()
        dates_covered = set()
        today = datetime.datetime.now()
        beginning_of_last_month = (today - datetime.timedelta(days=31)).replace(day=1, hour=0, minute=0, second=0)
        one_week_ago = today - datetime.timedelta(days=7)

        # Keep the last 10 files
        keep_files.update(files[-10:])

        for file in files:
            file_name = os.path.basename(file)
            file_date = datetime.datetime.strptime(file_name, data_name+"_%Y%m%d_%H%M%S.csv.gz")

            # For files older than 1 month, keep the first file of the month
            if file_date < beginning_of_last_month:
                month_start = file_date.replace(day=1, hour=0, minute=0, second=0)
                if month_start not in dates_covered:
                    dates_covered.add(month_start)
                    # logger.info(f"Kept file {file} because of month")
                    keep_files.add(file)

            # For files older than 1 week, keep the first file of a day
            elif file_date < one_week_ago:
                day_start = file_date.replace(hour=0, minute=0, second=0)
                if day_start not in dates_covered:
                    dates_covered.add(day_start)
                    # logger.info(f"Kept file {file} because of week")
                    keep_files.add(file)

            else:
                # logger.info(f"Kept file {file} because of young")
                keep_files.add(file)

        files_to_remove = set(files) - keep_files
        if files_to_remove:
            logger.info(f"Clean the old files: {files_to_remove}")
            for file_to_remove in files_to_remove:
                os.remove(file_to_remove)

    @staticmethod
    def dump_database_table(table: str):
        # To load last changes on production instance
        call_command(
            "dumpdata", "cycle." + table, output=os.path.join(BACKUP_FOLDER, table + "_dump.json.gz")
        )

    def backup_table(self, data_name: str, data: bytes, csv_dump: bool = True):
        if csv_dump:
            self.remove_old_files(data_name)
            with gzip.open(os.path.join(BACKUP_FOLDER,
                                        datetime.datetime.now(datetime.timezone.utc).strftime(data_name + '_%Y%m%d_%H%M%S.csv.gz')
                                        ), "w") as f:
                f.write(data)

        self.dump_database_table(data_name)

    @staticmethod
    def iter_json_dump_objects(filename: str, chunk_size: int = 1 << 20):
        """ Yields the objects of a (gzipped) dumpdata JSON list one by one, without loading the whole file.
        dumpdata writes the list in a single line, so it can't be read line by line """
        decoder = json.JSONDecoder()
        with gzip.open(filename, "rt", encoding="utf-8") as f:
            buffer = ""
            pos = 0
            eof = False
            while True:
                # skip the list syntax between objects
                while pos < len(buffer) and buffer[pos] in "[], \n\r\t":
                    pos += 1
                if pos >= len(buffer):
                    if eof:
                        return
                    buffer = f.read(chunk_size)
                    pos = 0
                    eof = not buffer
                    continue
                try:
                    # the top level entries are objects, so a cut-off entry always fails to decode
                    obj, end = decoder.raw_decode(buffer, pos)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    # entry is incomplete, read more data
                    more = f.read(chunk_size)
                    eof = not more
                    buffer = buffer[pos:] + more
                    pos = 0
                    continue
                yield obj
                pos = end

    # JSON values of these field types can be written to the database without conversion
    JSON_NATIVE_FIELD_TYPES = {
        "AutoField", "BigAutoField", "SmallAutoField", "IntegerField", "BigIntegerField", "SmallIntegerField",
        "PositiveIntegerField", "PositiveBigIntegerField", "PositiveSmallIntegerField", "FloatField", "CharField",
        "TextField", "BooleanField",
    }

    def bulk_load_json_dump(self, filename: str, model, batch_size: int = 5000) -> int:
        """ Fast replacement for loaddata for big tables (no signals, no model instances): new objects are inserted
        and existing objects (same primary key) are updated, as loaddata would do. Each batch is its own short
        transaction, so the database isn't locked for other requests during the whole import """
        model_label = model._meta.label_lower
        pk = model._meta.pk
        fields = [field for field in model._meta.concrete_fields if not field.primary_key]

        def converter(field):
            """ Returns a function that converts the JSON value of the field to the database value """
            if field.is_relation:
                target = field.target_field
                if target.get_internal_type() in self.JSON_NATIVE_FIELD_TYPES:
                    return None
                return lambda value: target.get_db_prep_save(target.to_python(value), connection)
            if field.get_internal_type() in self.JSON_NATIVE_FIELD_TYPES:
                return None
            return lambda value: field.get_db_prep_save(field.to_python(value), connection)

        pk_converter = converter(pk)
        converters = [(field.name, converter(field), field.get_default()) for field in fields]

        quote = connection.ops.quote_name
        columns = [pk.column] + [field.column for field in fields]
        sql = (
            f"INSERT INTO {quote(model._meta.db_table)} ({', '.join(quote(c) for c in columns)}) "
            f"VALUES ({', '.join(['%s'] * len(columns))}) "
            f"ON CONFLICT({quote(pk.column)}) DO UPDATE SET "
            + ", ".join(f"{quote(c)} = excluded.{quote(c)}" for c in columns[1:])
        )

        def save_batch(rows):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.executemany(sql, rows)

        batch = []
        count = 0
        for obj in self.iter_json_dump_objects(filename):
            if obj.get("model") != model_label:
                raise DeserializationError(f"Invalid model identifier: {obj.get('model')} (expected {model_label})")
            obj_fields = obj["fields"]
            row = [obj["pk"] if pk_converter is None else pk_converter(obj["pk"])]
            for name, convert, default in converters:
                value = obj_fields.get(name, default)
                row.append(value if convert is None or value is None else convert(value))
            batch.append(row)
            if len(batch) >= batch_size:
                save_batch(batch)
                count += len(batch)
                batch = []
        if batch:
            save_batch(batch)
            count += len(batch)
        return count

    def load_database_dump(self, data_name: str, bulk_model=None):
        """ Loads the dump of data_name if it changed since it was last loaded.
        :param bulk_model: if given, the dump is loaded with bulk_load_json_dump into this model (faster for big tables)
        """
        database_dump_file = data_name + '_dump.json.gz'
        # "load_db_dump_at_startup" is mountpoint in Docker
        filename = os.path.join("load_db_dump_at_startup", database_dump_file)
        if not os.path.isfile(filename):
            if self.warn_db_dump_not_found:
                logger.warning(self.warn_db_dump_not_found.pop())
            return False

        file_changed = os.path.getmtime(filename)

        if self.file_changed_last_loaded.get(database_dump_file):
            if file_changed <= self.file_changed_last_loaded[database_dump_file]:
                return False
            else:
                logger.info(f"Load database dump {database_dump_file} as it has changed.")

        try:
            # This will not remove data and just add data or replace data with the same primary key
            if bulk_model is None:
                call_command("loaddata", filename)
            else:
                start = time.time()
                count = self.bulk_load_json_dump(filename, bulk_model)
                logger.info(f"Bulk loaded {count} objects from {database_dump_file} in {time.time() - start:.1f}s")
        except DeserializationError as e:
            if str(e).find("Invalid model identifier") != -1:
                logger.error(f"Deserialiser Error: {e}")
                return False
            else:
                raise
        except (CommandError, OperationalError, IntegrityError, ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"Couldn't load backup {database_dump_file}: {e}")
            return False

        self.__class__.file_changed_last_loaded[database_dump_file] = file_changed
        logger.info(f"Loaded database dump {database_dump_file}.")
        return True

    def load_backup_mysql_based(self):
        """ Import the backup from the MySQL based version into this version
        - only required once, the file is the last one created by the mysql-based version
        """
        return self.load_csv_data(os.path.join(BACKUP_FOLDER, "20230722_070547.csv.gz"))

    def load_csv_data(self, filename):
        """
        - takes a long time for 3k entries as it only does about 5 entries per second (faster after disabling the backup)
        """
        def str_to_timedelta(text):
            data = [int(ii) for ii in (":0:0:" + text).rsplit(":", 3)[-3:]]
            return datetime.timedelta(hours=data[-3], minutes=data[-2], seconds=data[-1])

        if os.path.isfile(filename):
            number_of_imports = 0
            with gzip.open(filename, "r") as f:
                for line in f.readlines():
                    line = line.decode().split(";")      # 2008-06-12;14.94;00:38:40;247.0;11:21:00
                    if len(line) < 5 or len(line[0]) < 5:   # skip empty lines or lines without a date
                        continue
                    date = datetime.datetime.strptime(line[0], "%Y-%m-%d").date()
                    distance = float(line[1])
                    duration = str_to_timedelta(line[2])
                    totaldistance = float(line[3])
                    totalduration = str_to_timedelta(line[4])
                    bicycle = None
                    if len(line) >= 6:
                        bicycle = cycle.models.Bicycles(id=int(line[5]))
                    try:
                        obj = cycle.models.CycleRides.objects.get(date=date, distance=distance, duration=duration)
                    except cycle.models.CycleRides.DoesNotExist:
                        if bicycle:
                            obj = cycle.models.CycleRides(
                                date=date, distance=distance, duration=duration,
                                totaldistance=totaldistance, totalduration=totalduration, bicycle=bicycle
                            )
                        else:
                            obj = cycle.models.CycleRides(
                                date=date, distance=distance, duration=duration,
                                totaldistance=totaldistance, totalduration=totalduration
                            )
                        obj.save(run_backup=False, run_summary=False, run_cumulative=False)
                        number_of_imports += 1
            if number_of_imports:
                data_string = ""
                for obj in cycle.models.Bicycles.objects.all():
                    data_string += f"{obj.description};{obj.notes}\n"
                self.backup_table(cycle.models.Bicycles.table_name, data_string.encode())
                logger.info(f"Imported {number_of_imports} entries from {filename}")
                return True

        return False

    def load_backup_GeoLocateData_file_based(self):
        """ Import the backup from the MySQL based version into this version
        - only required once
        """
        filename = "/home/ronny/Documents/gps-logger/gaw_orte.dat"
        if os.path.isfile(filename):
            number_of_imports = 0
            with open(filename, "r") as f:
                for line in f.readlines():
                    line = line.split('\t')     #Doebritschen	0.5	11.47738668186831	50.91977849605224
                    name = line[0]
                    radius = float(line[1])
                    lon = float(line[2])
                    lat = float(line[3])
                    try:
                        obj = cycle.models.GeoLocateData.objects.get(name=name, latitude=lat, longitude=lon)
                    except cycle.models.GeoLocateData.DoesNotExist:
                        obj = cycle.models.GeoLocateData(
                            name=name, latitude=lat, longitude=lon, radius=radius
                        )
                        obj.save(run_backup=False)
                        number_of_imports += 1
            if number_of_imports:
                logger.info(f"Imported {number_of_imports} entries from {filename}")
                self.dump_GeoLocateData_dbs()
                return True
