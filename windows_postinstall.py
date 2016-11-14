import platform
import subprocess
import os
import sys

# Set firewall rules for the ICE-Adapter http://stackoverflow.com/a/3565942
program_path = os.path.join(os.getcwd(), "faf-ice-adapter.exe")
rule_name = 'FAF-ICE-Adapter'

print("Hello from postinstall", sys.argv, program_path)

if sys.argv[1] == "-install":
    #windows XP
    if platform.version().startswith('5'):
        subprocess.call(["netsh",
                         "firewall",
                         "add",
                         "allowedprogram",
                         "mode=ENABLE",
                         "profile=ALL,"
                         "name=\"{}\"".format(rule_name),
                         "program=\"{}\"".format(program_path)])

    else:
        subprocess.call(["netsh",
                         "advfirewall",
                         "firewall",
                         "add",
                         "rule",
                         "action=allow",
                         "profile=any",
                         "protocol=any",
                         "enable=yes",
                         "direction=in",
                         "name=\"{}\"".format(rule_name),
                         "program=\"{}\"".format(program_path)])
elif sys.argv[1] == "-remove":
    #windows XP
    if platform.version().startswith('5'):
        subprocess.call(["netsh",
                         "firewall",
                         "delete",
                         "allowedprogram",
                         "profile=ALL,"
                         "program=\"{}\"".format(program_path)])
    else:
        subprocess.call(["netsh",
                         "advfirewall",
                         "firewall",
                         "delete",
                         "rule",
                         "profile=any",
                         "name=\"{}\"".format(rule_name)])