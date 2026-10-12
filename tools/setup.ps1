# Установка VisualState-Kit на машине.
#
# Запуск из любого места после клонирования:
#     powershell -ExecutionPolicy Bypass -File tools\setup.ps1
#
# Что делает:
#   1. junction ~\.claude\skills\visualstate и ~\.kimi-code\skills\visualstate
#      -> <корень>\skill (скилл виден Claude Code и Kimi Code);
#   2. переменная VSKIT_HOME в профиле пользователя;
#   3. хук commit-msg (core.hooksPath = tools/hooks), локальный стоп-лист
#      tools\stoplist.txt (в .gitignore), напоминание об авторе коммитов;
#   4. Python 64-bit и lxml (проверка моделей схемой Visual State);
#   5. IAR Visual State, лицензия и arm-none-eabi-gcc.
#
# Прав администратора не требует: junction (mklink /J) создаётся без них.
# Файл сохранён в UTF-8 с BOM: без него Windows PowerShell 5.1 читает
# кириллицу в ANSI и падает на первой русской строке.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Write-Host "Корень набора: $root"
if (-not (Test-Path (Join-Path $root "vskit"))) {
    throw "В $root нет папки vskit — скрипт запущен не из репозитория."
}

$target = Join-Path $root "skill"
foreach ($skills in @(
    (Join-Path $env:USERPROFILE ".claude\skills"),
    (Join-Path $env:USERPROFILE ".kimi-code\skills"))) {
    if (-not (Test-Path $skills)) {
        New-Item -ItemType Directory -Path $skills -Force | Out-Null
    }
    $link = Join-Path $skills "visualstate"
    if (Test-Path $link) {
        $item = Get-Item $link -Force
        $current = $null
        if ($item.LinkType) { $current = $item.Target | Select-Object -First 1 }
        if ($current -eq $target) {
            Write-Host "OK   junction уже указывает куда нужно: $link"
        } else {
            if (-not $item.LinkType) {
                throw "$link — обычная папка, а не ссылка. Уберите её вручную и повторите."
            }
            Write-Host "     junction $link ведёт в другое место ($current) — пересоздаю"
            cmd /c rmdir "$link" | Out-Null
            cmd /c mklink /J "$link" "$target" | Out-Null
            Write-Host "OK   junction создан: $link -> $target"
        }
    } else {
        cmd /c mklink /J "$link" "$target" | Out-Null
        Write-Host "OK   junction создан: $link -> $target"
    }
}

[Environment]::SetEnvironmentVariable("VSKIT_HOME", $root, "User")
$env:VSKIT_HOME = $root
Write-Host "OK   VSKIT_HOME = $root (в новых консолях подхватится сам)"

if (Get-Command git -ErrorAction SilentlyContinue) {
    Push-Location $root
    git config core.hooksPath tools/hooks
    $author = git config --local --get user.email
    Pop-Location
    Write-Host "OK   core.hooksPath = tools/hooks (проверка текста коммита)"
    Write-Host "     папку текущего проекта можно добавить к стоп-словам:"
    Write-Host "     git config vskit.project '<путь к папке проекта>'"
    if ($author) {
        Write-Host "OK   автор коммитов этого клона: $author"
    } else {
        Write-Host "НЕТ  автор коммитов не задан — уйдут глобальные (рабочие) имя и адрес."
        Write-Host "     git config user.name  '<публичное имя>'"
        Write-Host "     git config user.email '<публичный адрес>'"
    }
} else {
    Write-Host "НЕТ  git не найден — хук commit-msg не включён"
}
$stop = Join-Path $root "tools\stoplist.txt"
if (-not (Test-Path $stop)) {
    $text = "# Стоп-слова: названия и приметы изделий этой машины.`r`n" +
            "# Файл ЛОКАЛЬНЫЙ: он в .gitignore и в репозиторий не попадает.`r`n" +
            "# Строка = подстрока, регистр не важен; # — комментарий.`r`n"
    [IO.File]::WriteAllText($stop, $text, (New-Object Text.UTF8Encoding $false))
    Write-Host "OK   заведён tools\stoplist.txt — впишите туда изделие до первого коммита"
} else {
    Write-Host "OK   tools\stoplist.txt на месте (локальный, в .gitignore)"
}

$py = $null
foreach ($c in @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe")) {
    if (Test-Path $c) { $py = $c; break }
}
if (-not $py) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source }
}
if (-not $py) {
    Write-Host "НЕТ  Python не найден."
    Write-Host "     winget install --id Python.Python.3.13 --scope user --silent"
    exit 1
}
Write-Host "OK   Python: $py"
$arch = & $py -c "import platform; print(platform.architecture()[0])"
if ($arch -ne "64bit") {
    Write-Host "НЕТ  Python $arch — нужен 64bit (StateMachineAPI64.dll)."
    exit 1
}

$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $py -c "import lxml" 2>&1 | Out-Null
$hasLxml = ($LASTEXITCODE -eq 0)
if (-not $hasLxml) {
    Write-Host "     lxml не установлен — ставлю"
    & $py -m pip install --quiet lxml
}
Write-Host "OK   lxml на месте"

& $py -c "import sys; sys.path.insert(0, r'$root'); import vskit as vk; vk.utf8_console(); print('OK   vskit', vk.__version__); print('OK   Visual State:', vk.vs_root(), vk.version()); print('OK   лицензия' if vk.license_ok()[0] else 'НЕТ  лицензии Visual State — Coder и Verificator не запустятся'); print('OK   arm-none-eabi-gcc', vk.gcc_version(), vk.gcc_bin())"
if ($LASTEXITCODE -ne 0) {
    Write-Host "НЕТ  Visual State или GCC не найдены: VSKIT_VSROOT, VSKIT_GCC (или MCU-Kit, MCUKIT_HOME)"
}
$ErrorActionPreference = $prev

Write-Host ""
Write-Host "Готово. Перезапустите Claude Code и Kimi Code, чтобы они увидели скилл (/visualstate и /skill:visualstate)."
