# v6-op 虚拟环境说明

本项目统一使用项目内虚拟环境：

```powershell
F:\v.6\v6-op\.venv\Scripts\python.exe
```

不要用系统 Python 直接运行 v6-op 服务、测试或验证脚本。

## 如果误删了 .venv

如果只是刚删掉，并且还在回收站里，恢复到原路径：

```text
F:\v.6\v6-op\.venv
```

通常还能继续用。恢复后验证：

```powershell
cd F:\v.6\v6-op
.\.venv\Scripts\python.exe -c "import sys, pywencai, akshare, pandas; print(sys.executable); print('deps_ok')"
```

如果输出 `deps_ok`，说明恢复成功。

## 如果恢复后不能用

直接重建，不需要手工修里面的文件：

```powershell
cd F:\v.6\v6-op
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

然后再验证：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 真正重要、不要误删的文件

- `.env`：保存 API key 和运行配置，不能提交，也不要随便删。
- `requirements.txt`：记录依赖清单，用来重建 `.venv`。
- `.venv\pyvenv.cfg`：虚拟环境自己的配置文件，恢复 `.venv` 时应一起恢复。

`.venv` 本身是可重建资产；`.env` 才是需要特别小心保管的本地配置。

## 标准启动命令

```powershell
cd F:\v.6\v6-op
.\.venv\Scripts\python.exe scripts\v6op_server.py --bind 10.10.10.186 --port 8900
```
