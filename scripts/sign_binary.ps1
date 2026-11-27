<#
.SYNOPSIS
    Firma digital de binarios e instaladores para el ecosistema Media Hub.
    Soporta certificados PFX persistentes (vía secretos MEDIAHUB_CERT_BASE64 / MEDIAHUB_CERT_PASSWORD
    o parámetro -PfxPath) con timestamping RFC 3161 (DigiCert / Sectigo / GlobalSign).

.PARAMETER FilePath
    Ruta del ejecutable o instalador a firmar.
.PARAMETER PfxPath
    (Opcional) Ruta de certificado PFX existente.
.PARAMETER PfxPassword
    (Opcional) Contraseña del PFX.
.PARAMETER RequireCert
    (Opcional) Si se especifica, falla si no se entrega un certificado persistente (PFX o MEDIAHUB_CERT_BASE64).
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,

    [Parameter(Mandatory=$false)]
    [string]$PfxPath = "",

    [Parameter(Mandatory=$false)]
    [string]$PfxPassword = "",

    [Parameter(Mandatory=$false)]
    [switch]$RequireCert
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $FilePath)) {
    Write-Error "El archivo especificado no existe: $FilePath"
    exit 1
}

$resolvedFile = (Resolve-Path $FilePath).Path
Write-Host "Iniciando proceso de firma digital para: $resolvedFile" -ForegroundColor Cyan

$cert = $null
$tempPfx = $null

try {
    $keyFlags = [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::UserKeySet -bor `
                [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable

    # 1. Cargar certificado persistente desde archivo PFX o secreto MEDIAHUB_CERT_BASE64
    if ($PfxPath -and (Test-Path $PfxPath)) {
        $resolvedPfx = (Resolve-Path $PfxPath).Path
        Write-Host "Cargando certificado desde $resolvedPfx..." -ForegroundColor Yellow
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($resolvedPfx, $PfxPassword, $keyFlags)
    } elseif (-not [string]::IsNullOrWhiteSpace($env:MEDIAHUB_CERT_BASE64)) {
        Write-Host "Cargando certificado persistente desde secreto MEDIAHUB_CERT_BASE64..." -ForegroundColor Yellow
        $certBytes = [Convert]::FromBase64String($env:MEDIAHUB_CERT_BASE64.Trim())
        $tempPfx = Join-Path ([System.IO.Path]::GetTempPath()) ("mediahub_cert_" + [Guid]::NewGuid().ToString("N") + ".pfx")
        [System.IO.File]::WriteAllBytes($tempPfx, $certBytes)
        $pass = if ($null -ne $env:MEDIAHUB_CERT_PASSWORD) { $env:MEDIAHUB_CERT_PASSWORD } else { "" }
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($tempPfx, $pass, $keyFlags)
    } else {
        if ($RequireCert) {
            Write-Error "No se encontró certificado persistente (-PfxPath ni MEDIAHUB_CERT_BASE64) y -RequireCert está activo."
            exit 1
        }

        if ($env:GITHUB_ACTIONS -eq "true") {
            Write-Host "::warning::MEDIAHUB_CERT_BASE64 no está configurado en este repositorio/organización. Se usará un certificado autofirmado efímero que NO conserva reputación entre versiones."
        }

        # 2. Fallback local: buscar certificado existente en el almacén del usuario o generar uno autofirmado
        $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
            Where-Object { $_.Subject -like "*Media Hub*" -or $_.Subject -like "*Alan Dave*" } |
            Sort-Object NotAfter -Descending |
            Select-Object -First 1

        if (-not $cert) {
            Write-Host "Generando certificado de firma de código autofirmado (fallback)..." -ForegroundColor Yellow
            $cert = New-SelfSignedCertificate `
                -Type CodeSigningCert `
                -Subject "CN=Media Hub (Alan Dave), O=Media-Hub-Site, C=CL" `
                -CertStoreLocation "Cert:\CurrentUser\My" `
                -KeyUsage DigitalSignature `
                -KeySpec Signature `
                -KeyLength 2048 `
                -HashAlgorithm "SHA256" `
                -NotAfter (Get-Date).AddYears(5)
            Write-Host "Certificado autofirmado creado con huella digital: $($cert.Thumbprint)" -ForegroundColor Yellow
        } else {
            Write-Host "Usando certificado local: $($cert.Subject) [Thumbprint: $($cert.Thumbprint)]" -ForegroundColor Green
        }
    }

    Write-Host "Certificado activo -> Subject: $($cert.Subject) | Issuer: $($cert.Issuer) | Thumbprint: $($cert.Thumbprint) | Expira: $($cert.NotAfter.ToString('yyyy-MM-dd'))" -ForegroundColor Cyan
    if ($cert.Subject -eq $cert.Issuer) {
        Write-Host "Nota: El certificado es autofirmado (Subject == Issuer). Para reputación automática en SmartScreen, reemplaza el secreto por un PFX emitido por una CA pública." -ForegroundColor DarkYellow
    }

    # 3. Firmar el archivo con marca de tiempo RFC 3161 (mantiene la validez tras la expiración del certificado)
    $timestampServers = @(
        "http://timestamp.digicert.com",
        "http://timestamp.sectigo.com",
        "http://timestamp.globalsign.com/tsa/r6advanced1"
    )

    $sig = $null
    $signed = $false
    foreach ($ts in $timestampServers) {
        try {
            Write-Host "Firmando con marca de tiempo de: $ts ..."
            $sig = Set-AuthenticodeSignature -FilePath $resolvedFile -Certificate $cert -TimestampServer $ts -HashAlgorithm "SHA256"
            if ($sig -and ($sig.Status -eq "Valid" -or $sig.Status -eq "UnknownError")) {
                # UnknownError ocurre en certificados autofirmados cuya raíz no está instalada en Trusted Root, pero la firma queda incrustada.
                Write-Host "Archivo firmado exitosamente. Estado: $($sig.StatusMessage) ($($sig.Status))" -ForegroundColor Green
                $signed = $true
                break
            } else {
                Write-Warning "Respuesta inesperada con $ts : $($sig.StatusMessage) ($($sig.Status)). Reintentando..."
            }
        } catch {
            Write-Warning "Fallo con $ts : $_. Reintentando con siguiente servidor..."
        }
    }

    if (-not $signed) {
        Write-Warning "Todos los servidores de marcas de tiempo fallaron. Firmando sin timestamp..."
        $sig = Set-AuthenticodeSignature -FilePath $resolvedFile -Certificate $cert -HashAlgorithm "SHA256"
        Write-Host "Resultado final: $($sig.StatusMessage) ($($sig.Status))" -ForegroundColor Yellow
    }

    if (-not $sig -or -not $sig.SignerCertificate) {
        Write-Error "Error: el archivo no quedó firmado correctamente ($resolvedFile)."
        exit 1
    }
} finally {
    if ($tempPfx -and (Test-Path $tempPfx)) {
        Remove-Item -Path $tempPfx -Force -ErrorAction SilentlyContinue
    }
}
