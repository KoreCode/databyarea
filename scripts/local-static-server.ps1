param(
  [string]$Root = (Get-Location).Path,
  [int]$Port = 8017
)

$ErrorActionPreference = 'Stop'
$rootPath = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), $Port)

$contentTypes = @{
  '.html' = 'text/html; charset=utf-8'
  '.css' = 'text/css; charset=utf-8'
  '.js' = 'application/javascript; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'
  '.png' = 'image/png'
  '.jpg' = 'image/jpeg'
  '.jpeg' = 'image/jpeg'
  '.svg' = 'image/svg+xml'
  '.ico' = 'image/x-icon'
  '.txt' = 'text/plain; charset=utf-8'
  '.xml' = 'application/xml; charset=utf-8'
}

function Send-Response {
  param(
    [System.Net.Sockets.NetworkStream]$Stream,
    [int]$StatusCode,
    [string]$StatusText,
    [byte[]]$Body,
    [string]$ContentType
  )

  try {
    $header = "HTTP/1.1 $StatusCode $StatusText`r`nContent-Type: $ContentType`r`nContent-Length: $($Body.Length)`r`nConnection: close`r`n`r`n"
    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
    $Stream.Write($headerBytes, 0, $headerBytes.Length)
    if ($Body.Length -gt 0) {
      $Stream.Write($Body, 0, $Body.Length)
    }
  } catch {
    # Browser refreshes/cancels can close the socket mid-write. Keep the server alive.
  }
}

function Send-Text {
  param(
    [System.Net.Sockets.NetworkStream]$Stream,
    [int]$StatusCode,
    [string]$StatusText,
    [string]$Body,
    [string]$ContentType = 'text/plain; charset=utf-8'
  )

  Send-Response $Stream $StatusCode $StatusText ([System.Text.Encoding]::UTF8.GetBytes($Body)) $ContentType
}

$listener.Start()
Write-Host "Serving $rootPath at http://127.0.0.1:$Port/"

try {
  while ($true) {
    $client = $listener.AcceptTcpClient()
    $client.ReceiveTimeout = 5000
    $client.SendTimeout = 5000
    try {
      $stream = $client.GetStream()
      $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::ASCII, $false, 4096, $true)
      $requestLine = $reader.ReadLine()

      if ([string]::IsNullOrWhiteSpace($requestLine)) {
        Send-Text $stream 400 'Bad Request' 'Bad request'
        continue
      }

      $parts = $requestLine.Split(' ')
      if ($parts.Length -lt 2 -or $parts[0] -ne 'GET') {
        Send-Text $stream 405 'Method Not Allowed' 'Method not allowed'
        continue
      }

      while ($stream.DataAvailable) {
        $line = $reader.ReadLine()
        if ([string]::IsNullOrEmpty($line)) { break }
      }

      $urlPath = $parts[1].Split('?')[0].TrimStart('/')
      $requestPath = [System.Uri]::UnescapeDataString($urlPath)

      if ($requestPath -like 'api/*') {
        Send-Text $stream 404 'Not Found' '{"error":"local static server has no API route"}' 'application/json; charset=utf-8'
        continue
      }

      if ([string]::IsNullOrWhiteSpace($requestPath)) {
        $requestPath = 'index.html'
      }

      $relativePath = $requestPath -replace '/', [System.IO.Path]::DirectorySeparatorChar
      $filePath = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($rootPath, $relativePath))

      if (!$filePath.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        Send-Text $stream 403 'Forbidden' 'Forbidden'
        continue
      }

      if ([System.IO.Directory]::Exists($filePath)) {
        $filePath = [System.IO.Path]::Combine($filePath, 'index.html')
      }

      if (![System.IO.File]::Exists($filePath)) {
        Send-Text $stream 404 'Not Found' 'Not found'
        continue
      }

      $extension = [System.IO.Path]::GetExtension($filePath).ToLowerInvariant()
      $contentType = if ($contentTypes.ContainsKey($extension)) { $contentTypes[$extension] } else { 'application/octet-stream' }
      Send-Response $stream 200 'OK' ([System.IO.File]::ReadAllBytes($filePath)) $contentType
    } catch {
      try {
        if ($stream -and $stream.CanWrite) {
          Send-Text $stream 500 'Internal Server Error' $_.Exception.Message
        }
      } catch {
        # Ignore per-request write failures so one aborted connection does not stop the listener.
      }
    } finally {
      if ($reader) { $reader.Dispose() }
      if ($stream) { $stream.Dispose() }
      $client.Close()
    }
  }
} finally {
  $listener.Stop()
}
