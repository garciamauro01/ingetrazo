// Windows Explorer thumbnail provider for .igz documents.
//
// The document is a ZIP container with the preview at meta/thumbnail.png.
// Explorer asks this COM object for a bitmap through IThumbnailProvider; the
// CLSID and registration live in installer/ingetrazo.iss (and, for development,
// in installer/register_user.ps1).
//
// Rebuild after any edit with installer\build-thumbnail-provider.ps1.

using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

// The [Registry] entry in ingetrazo.iss names this exact assembly version.
[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.0.0.0")]

namespace IngeTrazo.Shell
{
    [ComImport]
    [Guid("e357fccd-a995-4576-b01f-234630154e96")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IThumbnailProvider
    {
        [PreserveSig]
        int GetThumbnail(uint cx, out IntPtr phbmp, out WTS_ALPHATYPE pdwAlpha);
    }

    public enum WTS_ALPHATYPE
    {
        WTSAT_UNKNOWN = 0,
        WTSAT_RGB = 1,
        WTSAT_ARGB = 2
    }

    [ComImport]
    [Guid("b824b49d-22ac-4161-ac8a-9916e8fa3f7f")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IInitializeWithStream
    {
        [PreserveSig]
        int Initialize(IStream pstream, uint grfMode);
    }

    [ComImport]
    [Guid("b725f130-47ef-101a-a5f1-02608c9eebac")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IInitializeWithFile
    {
        [PreserveSig]
        int Initialize([MarshalAs(UnmanagedType.LPWStr)] string pszFilePath,
                       uint grfMode);
    }

    [Guid("A4C84E91-2E97-4D99-8FE5-E8B2B7D60D2B")]
    [ClassInterface(ClassInterfaceType.None)]
    [ComVisible(true)]
    public class IngeTrazoThumbnailProvider : IThumbnailProvider,
                                              IInitializeWithStream,
                                              IInitializeWithFile
    {
        // Guard against a corrupt file making Explorer allocate without bound.
        private const long MaxDocumentBytes = 512L * 1024 * 1024;
        private const long MaxThumbnailBytes = 16L * 1024 * 1024;

        private byte[] _streamBytes;
        private string _filePath;

        public int Initialize(IStream pstream, uint grfMode)
        {
            if (pstream == null) return E_POINTER;
            try
            {
                using (var ms = new MemoryStream())
                {
                    byte[] buffer = new byte[8192];
                    IntPtr pcbRead = Marshal.AllocHGlobal(sizeof(int));
                    try
                    {
                        Marshal.WriteInt32(pcbRead, 0);
                        do
                        {
                            // ComTypes.IStream.Read throws on a failed HRESULT;
                            // the outer catch then lets Explorer fall back.
                            pstream.Read(buffer, buffer.Length, pcbRead);
                            int read = Marshal.ReadInt32(pcbRead);
                            if (read <= 0) break;
                            if (ms.Length + read > MaxDocumentBytes)
                                return E_FAIL;
                            ms.Write(buffer, 0, read);
                        }
                        while (true);
                    }
                    finally
                    {
                        Marshal.FreeHGlobal(pcbRead);
                    }
                    _streamBytes = ms.ToArray();
                }
                return S_OK;
            }
            catch
            {
                return E_FAIL;
            }
        }

        public int Initialize(string pszFilePath, uint grfMode)
        {
            if (string.IsNullOrEmpty(pszFilePath)) return E_POINTER;
            _filePath = pszFilePath;
            return S_OK;
        }

        public int GetThumbnail(uint cx, out IntPtr phbmp,
                                out WTS_ALPHATYPE pdwAlpha)
        {
            phbmp = IntPtr.Zero;
            pdwAlpha = WTS_ALPHATYPE.WTSAT_ARGB;

            try
            {
                byte[] raw = _streamBytes;
                if (raw == null && !string.IsNullOrEmpty(_filePath)
                                && File.Exists(_filePath))
                {
                    var info = new FileInfo(_filePath);
                    if (info.Length > MaxDocumentBytes) return E_FAIL;
                    using (var fs = new FileStream(_filePath, FileMode.Open,
                                                   FileAccess.Read,
                                                   FileShare.ReadWrite |
                                                   FileShare.Delete))
                    using (var ms = new MemoryStream())
                    {
                        fs.CopyTo(ms);
                        raw = ms.ToArray();
                    }
                }
                if (raw == null || raw.Length < 4) return E_FAIL;
                if (raw[0] != 0x50 || raw[1] != 0x4B ||
                    raw[2] != 0x03 || raw[3] != 0x04)
                    return E_FAIL;     // not a ZIP container

                using (var zipMs = new MemoryStream(raw, false))
                using (var archive = new ZipArchive(zipMs, ZipArchiveMode.Read))
                {
                    ZipArchiveEntry entry = FindThumbnail(archive);
                    if (entry == null || entry.Length > MaxThumbnailBytes ||
                        entry.Length == 0)
                        return E_FAIL;

                    using (var entryStream = entry.Open())
                    using (var imgMs = new MemoryStream())
                    {
                        entryStream.CopyTo(imgMs);
                        imgMs.Position = 0;
                        using (var bmp = new Bitmap(imgMs))
                        {
                            // The icon view asks for 48/256 px; the preview
                            // pane asks for more (or 0 = native size). Match
                            // what was asked in BOTH directions: returning a
                            // 256 px bitmap no matter what leaves the side
                            // preview tiny.
                            int wanted = cx > 0 ? (int)cx
                                                : Math.Max(bmp.Width,
                                                           bmp.Height);
                            wanted = Math.Max(16, Math.Min(wanted, 2048));
                            double scale = Math.Min((double)wanted / bmp.Width,
                                                    (double)wanted / bmp.Height);
                            int w = Math.Max(1, (int)Math.Round(bmp.Width * scale));
                            int h = Math.Max(1, (int)Math.Round(bmp.Height * scale));
                            using (var thumb = new Bitmap(w, h,
                                       PixelFormat.Format32bppArgb))
                            using (var g = Graphics.FromImage(thumb))
                            {
                                g.Clear(Color.Transparent);
                                g.InterpolationMode =
                                    InterpolationMode.HighQualityBicubic;
                                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                                g.DrawImage(bmp, new Rectangle(0, 0, w, h));
                                // Explorer owns the HBITMAP and frees it.
                                phbmp = thumb.GetHbitmap(
                                    Color.FromArgb(0, 0, 0, 0));
                            }
                            return S_OK;
                        }
                    }
                }
            }
            catch
            {
                if (phbmp != IntPtr.Zero)
                {
                    GdiDeleteObject(phbmp);
                    phbmp = IntPtr.Zero;
                }
                return E_FAIL;
            }
        }

        private static ZipArchiveEntry FindThumbnail(ZipArchive archive)
        {
            // The writer always uses meta/thumbnail.png. The other names are
            // accepted so documents made by earlier experiments still preview.
            string[] names = { "meta/thumbnail.png", "thumbnail.png",
                               "thumb.png" };
            foreach (string name in names)
            {
                ZipArchiveEntry exact = archive.GetEntry(name);
                if (exact != null) return exact;
            }
            foreach (ZipArchiveEntry entry in archive.Entries)
            {
                foreach (string name in names)
                {
                    if (string.Equals(entry.FullName, name,
                                      StringComparison.OrdinalIgnoreCase))
                        return entry;
                }
            }
            return null;
        }

        [DllImport("gdi32.dll")]
        private static extern bool DeleteObject(IntPtr hObject);

        private static void GdiDeleteObject(IntPtr hObject)
        {
            try { DeleteObject(hObject); } catch { /* best effort */ }
        }

        private const int S_OK = 0;
        private const int E_POINTER = -2147467261;   // 0x80004003
        private const int E_FAIL = -2147467259;      // 0x80004005
    }
}
