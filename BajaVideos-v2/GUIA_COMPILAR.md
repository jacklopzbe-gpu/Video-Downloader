# Cómo compilar BajaVideos v2 (sin tener Mac)

La compilación se hace gratis en la nube con **GitHub Actions**. Subes esta carpeta a GitHub y te devuelve el `.app` de Mac (Apple Silicon e Intel) y el `.exe` de Windows.

## Paso 1 — Crear el repositorio

1. Entra a [github.com](https://github.com) (crea cuenta si no tienes).
2. Botón **New repository** → nómbralo `bajavideos` → márcalo **Private** → **Create repository**.

## Paso 2 — Subir esta carpeta

Opción fácil (sin terminal): en la página del repo, **Add file → Upload files** y arrastra TODO el contenido de esta carpeta (`BajaVideos-v2`). Importante: la carpeta `.github` a veces no se arrastra porque está oculta — si es así, usa la opción con terminal.

Opción con terminal (desde esta carpeta):

```bash
git init
git add .
git commit -m "BajaVideos v2"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/bajavideos.git
git push -u origin main
```

## Paso 3 — Esperar la compilación

1. En el repo, pestaña **Actions**.
2. Verás "Compilar BajaVideos (Mac y Windows)" corriendo (~5-10 min).
3. Al terminar (palomita verde), entra al run y abajo en **Artifacts** descarga:
   - `BajaVideos-Mac-AppleSilicon` → Macs con chip M1/M2/M3/M4
   - `BajaVideos-Mac-Intel` → Macs Intel viejitas
   - `BajaVideos-Windows` → el .exe

## Paso 4 — Compartir

Manda a cada persona el ZIP de su plataforma **junto con `LEEME_MAC.txt`** (explica cómo abrir la app la primera vez, porque no está firmada por Apple).

## Publicar una versión (opcional, más pro)

Si creas un tag `v2.0` y lo subes, GitHub crea un **Release** con los 3 archivos listos para descargar con un link público:

```bash
git tag v2.0
git push origin v2.0
```

## Cuando TikTok/Instagram/YouTube "se rompan"

Estas plataformas cambian seguido y `yt-dlp` (el motor de descarga) se actualiza casi a diario. Si las descargas empiezan a fallar para todos, solo hay que **recompilar**: pestaña Actions → "Compilar BajaVideos" → **Run workflow**. Eso instala el yt-dlp más nuevo y genera apps frescas.

## Compilar a mano (si tienes la máquina)

- Mac: abre Terminal y corre `bash build_mac.sh` dentro de esta carpeta.
- Windows: doble clic a `build_windows.bat` (requiere Python instalado).

## Nota sobre la firma de Apple

El `.app` va firmado "ad-hoc" (gratis). Funciona bien, pero macOS pide confirmar la primera apertura (clic derecho → Abrir). Para que abra sin ningún aviso se necesita una cuenta Apple Developer (99 USD/año) y notarización — normalmente no vale la pena para uso interno.
