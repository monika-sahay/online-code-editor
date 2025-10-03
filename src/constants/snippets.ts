export const defaultPy = `# Python example
print("Hello from Python!")
x, y = 10, 5
print(f"{x} + {y} = {x + y}")
print(f"{x} * {y} = {x * y}")
`;

export const defaultR = `# R example
cat("Hello from R\\n")
x <- 10; y <- 5
cat(x, "+", y, "=", x + y, "\\n")
cat(x, "*", y, "=", x * y, "\\n")
`;

export const defaultJS = `// JavaScript example
console.log("Hello from JavaScript!");
const x = 10, y = 5;
console.log(\`\${x} + \${y} = \${x + y}\`);
console.log(\`\${x} * \${y} = \${x * y}\`);
`;

export const defaultBash = `#!/usr/bin/env bash
echo "Hello from Bash"
x=10; y=5
echo "$x + $y = $((x + y))"
`;

export const defaultCpp = `// C++ example
#include <iostream>
using namespace std;
int main() {
    int x = 10, y = 5;
    cout << "Hello from C++!" << endl;
    cout << x << " + " << y << " = " << x + y << endl;
    cout << x << " * " << y << " = " << x * y << endl;
    return 0;
}
`;

export const defaultJava = `// Java example
public class Main {
    public static void main(String[] args) {
        int x = 10, y = 5;
        System.out.println("Hello from Java!");
        System.out.println(x + " + " + y + " = " + (x + y));
        System.out.println(x + " * " + y + " = " + (x * y));
    }
}
`;

export const defaultGo = `// Go example
package main
import "fmt"

func main() {
    x, y := 10, 5
    fmt.Println("Hello from Go!")
    fmt.Printf("%d + %d = %d\\n", x, y, x+y)
    fmt.Printf("%d * %d = %d\\n", x, y, x*y)
}
`;

export const defaultJulia = `# Julia example
println("Hello from Julia!")
x, y = 10, 5
println("$(x) + $(y) = $(x + y)")
println("$(x) * $(y) = $(x * y)")
`;

export const defaultC = `// C example
#include <stdio.h>
int main() {
    int x = 10, y = 5;
    printf("Hello from C!\\n");
    printf("%d + %d = %d\\n", x, y, x + y);
    printf("%d * %d = %d\\n", x, y, x * y);
    return 0;
}
`;

export const defaultCSharp = `// C# example
using System;

class Program {
    static void Main() {
        int x = 10, y = 5;
        Console.WriteLine("Hello from C#!");
        Console.WriteLine($"{x} + {y} = {x + y}");
        Console.WriteLine($"{x} * {y} = {x * y}");
    }
}
`;
