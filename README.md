# Швейцарка для гугл-таблиц

## Инструкция

1. `pip install gspread networkx oauth2client PyOpenSSL`
2. Заведите Service Account на Google Developers по [инструкции](https://gspread.readthedocs.io/en/latest/oauth2.html#using-signed-credentials)
3. На client_email, который выглядит как `473000000000-yoursisdifferent@developer.gserviceaccount.com`, расшарьте свой док, чтобы можно было его редактировать
4. Скопируйте файл example_config.json и отредактируйте его так, чтобы данные соответствовали вашим нуждам (подробно расписывать лень, будут вопросы — пишите)
5. Запускать так: `python swiss_gsheets.py --config your_config_file.json`. После этого на каждое нажатие Enter будут выводиться новые пары на листе, указанном в `pairings_sheet_name`

Посмотреть пример работы можно в [табличке из example_config.json](https://docs.google.com/spreadsheets/d/1sWmm86ur8WvHMiNfeJugABPmWxQZlt9n1zlBCAcRHdk/edit#gid=303608029)