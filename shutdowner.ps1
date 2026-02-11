Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# --- Hide Console Window ---
Add-Type -Name Window -Namespace Console -MemberDefinition '[DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow(); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);'
[Console.Window]::ShowWindow([Console.Window]::GetConsoleWindow(), 0) | Out-Null

# --- Variables ---
$global:secondsLeft = 300
$global:isPostponed = $false
$global:wakeUpTime = [DateTime]::MinValue
$global:baseBg = [System.Drawing.Color]::FromArgb(25, 25, 30)
$global:alertBg = [System.Drawing.Color]::FromArgb(60, 20, 20) # Subtle dark red

# --- Create Form ---
$form = New-Object System.Windows.Forms.Form
$form.Text = "Emergency Shutdown"
$form.Size = New-Object System.Drawing.Size(850, 480)
$form.FormBorderStyle = 'None'
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.BackColor = $global:baseBg
$form.KeyPreview = $true

# --- UI Elements ---
$lbl = New-Object System.Windows.Forms.Label
$lbl.Text = "SYSTEM SHUTDOWN INITIATED"
$lbl.Font = New-Object System.Drawing.Font("Segoe UI", 26, [System.Drawing.FontStyle]::Bold)
$lbl.ForeColor = [System.Drawing.Color]::FromArgb(255, 80, 80)
$lbl.TextAlign = 'MiddleCenter'; $lbl.Dock = 'Top'; $lbl.Height = 120
$form.Controls.Add($lbl)

$lblCountdown = New-Object System.Windows.Forms.Label
$lblCountdown.Text = "05:00"
$lblCountdown.Font = New-Object System.Drawing.Font("Consolas", 45, [System.Drawing.FontStyle]::Bold)
$lblCountdown.ForeColor = [System.Drawing.Color]::White
$lblCountdown.TextAlign = 'MiddleCenter'; $lblCountdown.Dock = 'Top'; $lblCountdown.Height = 110
$form.Controls.Add($lblCountdown)

# --- Button Layout ---
$panel = New-Object System.Windows.Forms.FlowLayoutPanel
$panel.Dock = 'Bottom'; $panel.Height = 130; $panel.Padding = New-Object System.Windows.Forms.Padding(40, 10, 0, 0)
$form.Controls.Add($panel)

function Create-Btn($txt, $color, $script) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $txt; $b.Size = New-Object System.Drawing.Size(180, 75)
    $b.FlatStyle = 'Flat'; $b.ForeColor = 'White'; $b.BackColor = $color
    $b.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $b.FlatAppearance.BorderSize = 0
    $b.Add_Click($script)
    return $b
}

# 1. SHUT DOWN NOW
$btnNow = Create-Btn "SHUT DOWN NOW" ([System.Drawing.Color]::Maroon) {
    $timer.Stop(); $tray.Dispose(); $form.Close(); shutdown /s /t 60 /c "Your computer will shut down in 60 seconds. Please save your work."; Stop-Process -Id $PID
}
$panel.Controls.Add($btnNow)

# 2. POSTPONE LOGIC
$postponeLogic = {
    param($mins)
    $global:wakeUpTime = [DateTime]::Now.AddMinutes($mins)
    $global:isPostponed = $true
    $global:secondsLeft = 300 
    $form.Hide()
    $tray.ShowBalloonTip(3000, "Postponed", "System will notify you again in $mins minutes.", "Info")
}

$btn1 = Create-Btn "Postpone 1m" ([System.Drawing.Color]::FromArgb(50,50,60)) { &$postponeLogic 1 }
$btn5 = Create-Btn "Postpone 5m" ([System.Drawing.Color]::FromArgb(50,50,60)) { &$postponeLogic 5 }
$btn8 = Create-Btn "Postpone 8h" ([System.Drawing.Color]::FromArgb(50,50,60)) { &$postponeLogic 480 }

$panel.Controls.AddRange(@($btn1, $btn5, $btn8))

# --- System Tray ---
$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -Id $PID).MainModule.FileName)
$tray.Visible = $true
$tray.Text = "Shutdown Monitor Active"

$menu = New-Object System.Windows.Forms.ContextMenuStrip
$itemShow = $menu.Items.Add("Reset Window")
$itemShow.Add_Click({ $global:isPostponed = $false; $form.Show(); $form.Activate() })
$tray.ContextMenuStrip = $menu

# --- Timer & Pulse Logic ---
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000
$timer.Add_Tick({
    if ($global:isPostponed) {
        if ([DateTime]::Now -ge $global:wakeUpTime) {
            $global:isPostponed = $false
            $form.Show(); $form.Activate()
        }
    } else {
        $global:secondsLeft--
        $ts = [TimeSpan]::FromSeconds($global:secondsLeft)
        $lblCountdown.Text = "{0:mm\:ss}" -f $ts
        
        # --- Pulse/Flash Logic ---
        if ($global:secondsLeft -le 60) {
            if ($global:secondsLeft % 2 -eq 0) {
                $form.BackColor = $global:alertBg
                $lbl.BackColor = $global:alertBg
                $lblCountdown.BackColor = $global:alertBg
            } else {
                $form.BackColor = $global:baseBg
                $lbl.BackColor = $global:baseBg
                $lblCountdown.BackColor = $global:baseBg
            }
        }
        
        # Text color change for urgency
        if ($global:secondsLeft -le 20) { $lblCountdown.ForeColor = [System.Drawing.Color]::Yellow }

        if ($global:secondsLeft -le 0) {
            $timer.Stop(); $tray.Dispose(); $form.Close()
            #Stop-Computer -Force
            #Write-Host "Shutdown Command Sent"
            shutdown /s /t 60 /c "Your computer will shut down in 60 seconds. Please save your work."
			Stop-Process -Id $PID
        }
    }
})
$timer.Start()

# --- Emergency Quit: Ctrl+Alt+Shift+Q ---
$form.Add_KeyDown({
    param($s, $e)
    if ($e.Control -and $e.Alt -and $e.Shift -and ($e.KeyCode -eq 'Q')) {
        $tray.Dispose(); Stop-Process -Id $PID
    }
})

$form.Add_FormClosing({ param($s, $e) $e.Cancel = $true })

[System.Windows.Forms.Application]::Run($form)
