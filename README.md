requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

File "C:\Users\p90022569\Downloads\image_gen\venv\lib\site-packages\streamlit\runtime\scriptrunner\exec_code.py", line 128, in exec_func_with_error_handling
    result = func()
File "C:\Users\p90022569\Downloads\image_gen\venv\lib\site-packages\streamlit\runtime\scriptrunner\script_runner.py", line 669, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
File "C:\Users\p90022569\Downloads\image_gen\app.py", line 38, in <module>
    data = resp.json()
File "C:\Users\p90022569\Downloads\image_gen\venv\lib\site-packages\requests\models.py", line 980, in json
    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
