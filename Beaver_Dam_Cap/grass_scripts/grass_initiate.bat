set wrkdir=%1
set scrdir=%2
set burndem=%3
set so_vec=%4
set flwacc=%5

call grass78 -c EPSG:27700 %wrkdir% --gtext --exec %scrdir% %burndem% %so_vec% %flwacc%