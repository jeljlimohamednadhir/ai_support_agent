"""Deep discovery WA server."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from app.services.ssh_operations.client.ssh_client import SshClient

client = SshClient(
    host=os.getenv('SSH_WA_HOST'),
    port=22,
    username=os.getenv('SSH_WA_USER'),
    password=os.getenv('SSH_WA_PASSWORD'),
    connect_timeout_s=15,
    auto_add_host_key=True,
)
client.connect()
print("[OK] Connected to WA:", os.getenv('SSH_WA_HOST'))

cmds = [
    ("Tomcat logs dir", "ls -la /opt/application/49mapp/current/tomcat/00/logs/ 2>/dev/null | head -25"),
    ("Catalina.out tail", "tail -5 /opt/application/49mapp/current/tomcat/00/logs/catalina.out 2>/dev/null"),
    ("Brasil app logs", "find /opt/application/49mapp -maxdepth 5 -name '*.log' -type f 2>/dev/null | head -30"),
    ("Webapp dirs", "ls /opt/application/49mapp/current/tomcat/00/webapps/ 2>/dev/null"),
    ("UmiDico logs", "find /opt/application/49mapp/current/umidico -name '*.log' 2>/dev/null | head -10"),
    ("Recent logs modified today", "find /opt/application/49mapp -name '*.log' -mtime -1 2>/dev/null | head -20"),
    ("Log4j/logback configs", "find /opt/application/49mapp -maxdepth 5 -name 'log4j*' -o -name 'logback*' 2>/dev/null | head -10"),
    ("Brasil properties", "find /opt/application/49mapp -maxdepth 5 -name '*.properties' 2>/dev/null | grep -iv 'commvault' | head -20"),
]

for label, cmd in cmds:
    r = client.exec_command(cmd, timeout_s=15)
    out = r.get('output', '').strip()
    print(f"\n[{label}]")
    if out:
        for line in out.splitlines()[:25]:
            print(f"  {line}")
    else:
        print("  (empty)")

client.disconnect()
