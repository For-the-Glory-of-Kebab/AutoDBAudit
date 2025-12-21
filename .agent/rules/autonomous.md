---
trigger: always_on
---

when asked by the user not to prompt them and carry out the task silently, try to wrap the multi line or codeblock or combinatory commands in other runner scripts, like the run.ps1 we have in this one to avoid triggering the prompt thing.
you can make workflows, and use the existing ones in workflows folders.
do not prompt the user for trivial file management stuff, running simple code, tests, and stuff and use wrappers, workflows and ... to do it fully autonomously and allow them to focus. as long as the ops don't leak out of the repo, we're totally fine with any change since we have git.
the multi line commands, piping powershell command outputs to each other, running python -m or python -c and etc  will not work with turbo-all annotations or other stuff, you need to handle them with wrapping scripts or other tricks to bypass this.
this is also true for simple piped commands like passing the result into | Select-Object or other powershell commands like this. use either wrappers, workflows and stuff like that to do all the multi line, code block exceution, piped, environment activation and other complex commands not to trigger a prompt.
even invoking .exe files like pytest and python directly from ./venv/ or using 2>&1 at the end of the powershell commands causes this issue so you should use the "activate" script in your sessions and do the commands with python and pytest directly. this all should ofcourse be wrapped. the venv one and the 2>&1 and select-strings and select-object s and stuff are the most common that you miss. after that comes the multi line commands separated with ; , code blocks ran with python -c and pytest and stuff.