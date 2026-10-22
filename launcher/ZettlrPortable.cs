// Zettlr Portable: supported --data-dir switch, safe process lifecycle, bundled TraceGuard.
// MIT License — custom launcher, not an upstream Zettlr component.
using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Forms;

internal static class ZettlrPortable
{
    private static int Main(string[] args)
    {
        // IMPORTANT: all headless self-tests execute BEFORE file checks or dialogs.
        if (args.Length == 1 && args[0] == "--portable-self-test") return SelfTest();
        if (args.Length == 1 && args[0] == "--traceguard-self-test") return TraceGuard.SelfTest();
        if (args.Length == 1 && args[0] == "--registrytrace-self-test") return RegistryTraceGuard.SelfTest();
        try { return Launch(args); }
        catch (Exception ex)
        {
            MessageBox.Show("Zettlr Portable could not start.\r\n\r\n" + ex.Message,
                "Zettlr Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static int SelfTest()
    {
        string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
        string exe = Path.GetFullPath(Path.Combine(root, "App", "Zettlr", "Zettlr.exe"));
        string data = Path.GetFullPath(Path.Combine(root, "Data", "profile"));
        return (exe.StartsWith(root, StringComparison.OrdinalIgnoreCase) &&
            data.StartsWith(Path.Combine(root, "Data"), StringComparison.OrdinalIgnoreCase) &&
            !data.StartsWith(Path.Combine(root, "App"), StringComparison.OrdinalIgnoreCase)) ? 0 : 10;
    }

    private static int Launch(string[] passThrough)
    {
        string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
        string binary = Path.Combine(root, "App", "Zettlr", "Zettlr.exe");
        string profile = Path.Combine(root, "Data", "profile");
        string temp = Path.Combine(root, "Data", "Temp");
        string logs = Path.Combine(root, "Data", "TraceGuard");
        if (!File.Exists(binary)) throw new FileNotFoundException("App\\Zettlr\\Zettlr.exe is missing. Extract the complete application ZIP.");
        if (!File.Exists(Path.Combine(root, "App", "Zettlr", "resources", "app.asar")))
            throw new FileNotFoundException("The bundled Zettlr resources\\app.asar is missing.");
        // Refuse a concurrent installed/portable Zettlr process; protects profile and TraceGuard attribution.
        bool owned;
        using (Mutex mutex = new Mutex(true, @"Local\ZettlrPortable_" + Hash(profile), out owned))
        {
            if (!owned) throw new InvalidOperationException("This portable profile is already in use. Close the other Zettlr Portable window.");
            try
            {
                if (AnyZettlrRunning()) throw new InvalidOperationException(
                    "Another Zettlr instance is already running. Close it before launching the portable version, " +
                    "so Windows traces cannot be confused with another installation.");
                Directory.CreateDirectory(profile);
                Directory.CreateDirectory(temp);
                Directory.CreateDirectory(logs);
                TraceGuard files = new TraceGuard(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    Path.Combine(logs, "last-run.log"));
                RegistryTraceGuard registry = new RegistryTraceGuard(binary, Path.Combine(logs, "registry.log"));
                try
                {
                    ProcessStartInfo info = new ProcessStartInfo();
                    info.FileName = binary;
                    info.WorkingDirectory = Path.GetDirectoryName(binary);
                    info.UseShellExecute = false;
                    info.Arguments = Quote("--data-dir=" + profile);
                    foreach (string arg in passThrough)
                    {
                        // Prevent replacing the enforced profile with a later --data-dir argument.
                        if (arg.StartsWith("--data-dir", StringComparison.OrdinalIgnoreCase))
                            throw new ArgumentException("--data-dir is reserved for portable profile protection.");
                        info.Arguments += " " + Quote(arg);
                    }
                    info.EnvironmentVariables["TEMP"] = temp;
                    info.EnvironmentVariables["TMP"] = temp;
                    using (Process process = Process.Start(info))
                    {
                        if (process == null) throw new InvalidOperationException("Zettlr.exe did not start.");
                        process.WaitForExit();
                        return process.ExitCode;
                    }
                }
                finally
                {
                    // When Electron forks workers, allow them a short shutdown window.
                    if (AnyZettlrRunning()) Thread.Sleep(1500);
                    try { registry.Cleanup(); } finally { files.Cleanup(); }
                }
            }
            finally { mutex.ReleaseMutex(); }
        }
    }

    private static bool AnyZettlrRunning()
    {
        try
        {
            Process[] processes = Process.GetProcessesByName("Zettlr");
            bool result = processes.Length != 0;
            foreach (Process p in processes) p.Dispose();
            return result;
        }
        catch { return true; }
    }

    private static string Hash(string value)
    {
        using (SHA256 sha = SHA256.Create())
        {
            byte[] digest = sha.ComputeHash(Encoding.UTF8.GetBytes(Path.GetFullPath(value).ToUpperInvariant()));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 12; i++) sb.Append(digest[i].ToString("x2"));
            return sb.ToString();
        }
    }

    private static string Quote(string value)
    {
        // Windows CommandLineToArgvW-compatible quoting (incl. trailing backslashes).
        StringBuilder result = new StringBuilder("\"");
        int slash = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slash++; continue; }
            if (c == '"') { result.Append('\\', slash * 2 + 1); result.Append('"'); slash = 0; continue; }
            if (slash > 0) { result.Append('\\', slash); slash = 0; }
            result.Append(c);
        }
        if (slash > 0) result.Append('\\', slash * 2);
        return result.Append('"').ToString();
    }
}
