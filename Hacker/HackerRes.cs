// HackerRes.cs - icon resource DLL for Hacker Terminal.
// Icons are embedded as .NET resources; read them with GetIcon().

using System;
using System.IO;
using System.Reflection;

public static class HackerRes
{
    public static byte[] GetIcon(string name)
    {
        Assembly asm = Assembly.GetExecutingAssembly();
        using (Stream s = asm.GetManifestResourceStream(name))
        {
            if (s == null) return null;
            byte[] buf = new byte[s.Length];
            int off = 0;
            while (off < buf.Length)
            {
                int n = s.Read(buf, off, buf.Length - off);
                if (n <= 0) break;
                off += n;
            }
            return buf;
        }
    }

    public static string[] ListIcons()
    {
        return Assembly.GetExecutingAssembly().GetManifestResourceNames();
    }

    public static int Count()
    {
        return Assembly.GetExecutingAssembly().GetManifestResourceNames().Length;
    }
}
