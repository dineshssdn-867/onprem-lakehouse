
  
    

    create table "lakehouse"."dev_silver"."dim_date"
      
      
    as (
      

select
  year(calendarDate) * 10000 + month(calendarDate) * 100 + day(calendarDate) as dateInt,
  CalendarDate,
  year(calendarDate) AS CalendarYear,
  format_datetime(calendarDate, 'MMMM') as CalendarMonth,
  month(calendarDate) as MonthOfYear,
  format_datetime(calendarDate, 'EEEE') as CalendarDay,
  day_of_week(calendarDate) AS DayOfWeek,
  day_of_week(calendarDate) as DayOfWeekStartMonday,
  case
    when day_of_week(calendarDate) < 6 then 'Y'
    else 'N'
  end as IsWeekDay,
  day_of_month(calendarDate) as DayOfMonth,
  case
    when calendarDate = last_day_of_month(calendarDate) then 'Y'
    else 'N'
  end as IsLastDayOfMonth,
  day_of_year(calendarDate) as DayOfYear,
  week_of_year(calendarDate) as WeekOfYearIso,
  quarter(calendarDate) as QuarterOfYear,
  /* Use fiscal periods needed by organization fiscal calendar */
  case
    when month(calendarDate) >= 10 then year(calendarDate) + 1
    else year(calendarDate)
  end as FiscalYearOctToSep,
  (month(calendarDate) + 2) % 12 + 1 AS FiscalMonthOctToSep,
  case
    when month(calendarDate) >= 7 then year(calendarDate) + 1
    else year(calendarDate)
  end as FiscalYearJulToJun,
  (month(calendarDate) + 5) % 12 + 1 AS FiscalMonthJulToJun
from
    UNNEST(sequence(DATE '2010-01-01', DATE '2037-01-01', INTERVAL '1' DAY)) AS t(calendarDate)
order by
  calendarDate
    );

  