import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("[ERROR] Runner requires a Lua source file.")
        return 2
    source_path = Path(sys.argv[1])
    try:
        source = source_path.read_text(encoding="utf-8")
    except Exception as exc:
        print("[ERROR] Cannot read script: " + str(exc))
        return 2
    try:
        from lupa import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, register_builtins=False)
        g = lua.globals()
        def safe_print(*args):
            print(" ".join(str(x) for x in args), flush=True)
        g.print = safe_print
        # This is a limited standalone environment, not the Roblox client.
        for name in ("os", "io", "package", "debug", "dofile", "loadfile", "require"):
            g[name] = None
        g.loadstring = g.load
        try:
            result = lua.execute(source)
            if result is not None:
                safe_print(result)
            print("[OCEANA] Execution completed.", flush=True)
            return 0
        except Exception as exc:
            print("[LUA ERROR] " + str(exc), flush=True)
            return 1
    except ImportError:
        print("[ERROR] Lupa is missing. Run install.bat first.")
        return 3
    except Exception as exc:
        print("[ERROR] Runtime startup failed: " + str(exc))
        return 4

if __name__ == "__main__":
    raise SystemExit(main())
