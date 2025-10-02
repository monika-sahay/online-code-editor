import requests, sys, json, time

BASE = "http://127.0.0.1:8000"

def post(path, payload, timeout=25):
    r = requests.post(BASE + path, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def assert_ok(lang, code):
    print(f"\n--- {lang} ---")
    data = post("/execute", {"language": lang, "code": code})
    print(json.dumps(data, indent=2))
    assert data["success"], f"{lang} failed: {data['error']}"
    assert "Hello" in (data["output"] + data["error"]), f"{lang} no output"

def main():
    # simple hello tests for each runtime
    tests = [
        ("python", 'print("Hello from Python")'),
        ("bash", 'echo "Hello from Bash"'),
        ("javascript", 'console.log("Hello from JavaScript")'),
        ("r", 'cat("Hello from R\\n")'),
        ("go", 'package main\nimport "fmt"\nfunc main(){fmt.Println("Hello from Go")}\n'),
        ("julia", 'println("Hello from Julia")\n'),
        ("cpp", r'#include <iostream>\nint main(){std::cout<<"Hello from C++\\n";}'),
        ("java", 'public class Main{public static void main(String[] a){System.out.println("Hello from Java");}}'),
    ]
    for lang, code in tests:
        assert_ok(lang, code)

if __name__ == "__main__":
    sys.exit(main())
