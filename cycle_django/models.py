Read file: /home/ronny/Documents/Scripts/cycle_logging/fahrrad_mysql.params, using information: {'host': 'localhost', 'user': 'fahrrad', 'password': 'sx6_ehK6dvTxET9dk4HuP3Qup', 'db': 'fahrrad'}
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CycleFahrradRides(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(db_column='Date')  # Field name made lowercase.
    daykm = models.FloatField(db_column='DayKM')  # Field name made lowercase.
    dayseconds = models.PositiveIntegerField(db_column='DaySeconds')  # Field name made lowercase.
    totalkm = models.FloatField(db_column='TotalKM')  # Field name made lowercase.
    totalseconds = models.PositiveIntegerField(db_column='TotalSeconds')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'cycle_fahrrad_rides'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class FahrradMonthlySummary(models.Model):
    month_starting_on = models.DateField(db_column='Month_starting_on', primary_key=True)  # Field name made lowercase.
    monthkm = models.FloatField(db_column='MonthKM')  # Field name made lowercase.
    monthseconds = models.IntegerField(db_column='MonthSeconds')  # Field name made lowercase.
    monthkmh = models.FloatField(db_column='MonthKMH', blank=True, null=True)  # Field name made lowercase.
    monthdays = models.IntegerField(db_column='MonthDays', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_monthly_summary'


class FahrradRides(models.Model):
    entryid = models.AutoField(db_column='EntryID', primary_key=True)  # Field name made lowercase.
    date = models.DateField(db_column='Date')  # Field name made lowercase.
    daykm = models.FloatField(db_column='DayKM')  # Field name made lowercase.
    dayseconds = models.IntegerField(db_column='DaySeconds')  # Field name made lowercase.
    daykmh = models.FloatField(db_column='DayKMH', blank=True, null=True)  # Field name made lowercase.
    totalkm = models.FloatField(db_column='TotalKM', unique=True)  # Field name made lowercase.
    totalseconds = models.IntegerField(db_column='TotalSeconds')  # Field name made lowercase.
    totalkmh = models.FloatField(db_column='TotalKMH', blank=True, null=True)  # Field name made lowercase.
    culmkm = models.FloatField(db_column='CulmKM', blank=True, null=True)  # Field name made lowercase.
    culmseconds = models.IntegerField(db_column='CulmSeconds', blank=True, null=True)  # Field name made lowercase.
    wasupdated = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fahrrad_rides'
        unique_together = (('date', 'daykm', 'dayseconds'),)


class FahrradWeeklySummary(models.Model):
    week_starting_on = models.DateField(db_column='Week_starting_on', primary_key=True)  # Field name made lowercase.
    weekkm = models.FloatField(db_column='WeekKM')  # Field name made lowercase.
    weekseconds = models.IntegerField(db_column='WeekSeconds')  # Field name made lowercase.
    weekkmh = models.FloatField(db_column='WeekKMH', blank=True, null=True)  # Field name made lowercase.
    weekdays = models.IntegerField(db_column='WeekDays', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_weekly_summary'


class FahrradYearlySummary(models.Model):
    year_starting_on = models.DateField(db_column='Year_starting_on', primary_key=True)  # Field name made lowercase.
    yearkm = models.FloatField(db_column='YearKM')  # Field name made lowercase.
    yearseconds = models.IntegerField(db_column='YearSeconds')  # Field name made lowercase.
    yearkmh = models.FloatField(db_column='YearKMH', blank=True, null=True)  # Field name made lowercase.
    yeardays = models.IntegerField(db_column='YearDays')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_yearly_summary'
