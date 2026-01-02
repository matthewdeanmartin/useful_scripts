# Get-BootShutdownEvents.ps1

$lastWeek = (Get-Date).AddDays(-7)

# XML Filter for events 6005 (boot) and 6006 (shutdown)
$filterXml = @"
<QueryList>
  <Query Id="0" Path="System">
    <Select Path="System">
      *[System[
        (EventID=6005 or EventID=6006) and
        TimeCreated[@SystemTime >= '$($lastWeek.ToUniversalTime().ToString("o"))']
      ]]
    </Select>
  </Query>
</QueryList>
"@

# Fetch and display the events
Get-WinEvent -FilterXml $filterXml |
  Sort-Object TimeCreated |
  ForEach-Object {
    $eventType = switch ($_.Id) {
      6005 { "Boot (EventID 6005 - Event Log Started)" }
      6006 { "Shutdown (EventID 6006 - Event Log Stopped)" }
      default { "Other" }
    }

    [PSCustomObject]@{
      Timestamp = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
      Type      = $eventType
    }
  } | Format-Table -AutoSize
