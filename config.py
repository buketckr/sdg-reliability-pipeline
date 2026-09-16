import os

RUN = int(
    os.getenv(
        "RUN",
        "16"
    )
)

RUN_SOURCE = os.getenv(
    "RUN_SOURCE",
    "experiment"
)


if RUN_SOURCE == "frontend":
    RUN_DIR = f"frontend_run{RUN}"
else:
    RUN_DIR = f"run{RUN}"






#run 3 ve 4 ve 5 (4,5 0 ve 1 in kopyalanıp 3/2 kuralı yerine 4/1 alınmış hali. 0 runı yapay bir run. aynı zamandada run 5 o yapay runı kullandı. ran 3 ve run 4 asıl runların 3/2 yerine 4/1 alması için gönderilen hali)
#run 6 prompTemplate ile runlandı
#run7 promptTemplate_strict ile runlandı.
 #run 8 run 1 nın kopyası ama stage_advanced de kullanıldı.
 #run 9 run 2 nin kopyası ama stage_advanced de kullanıldı.
 # run10 run run6 in kopyası ama stage_advanced de kullanıldı
 #run11 normal run, stage advanced le stageler gecirildi.
 #run 12 ve run13 , ve 14, 15, 16stage advanced ve LAST 9 COURSES LA YAPILDI, şuana kadar ilk kez
 

 #NORMAL RUNLAR: 2,3,6,11, 12, 13, 14, 15