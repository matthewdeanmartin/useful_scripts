#!/usr/bin/env bash

set -eou pipefail

bootlog::get_event_log_data() {
  # Uses PowerShell to get boot/shutdown event times for the last 7 days.
  powershell.exe -NoProfile -Command '
    $lastWeek = (Get-Date).AddDays(-7)
    $filter = @"
<QueryList>
  <Query Id="0" Path="System">
    <Select Path="System">
      *[System[(
        (EventID=6005 or EventID=6006) and
        TimeCreated[@SystemTime>='''"$($lastWeek.ToUniversalTime().ToString("o"))"''']
      )]]
    </Select>
  </Query>
</QueryList>
"@
    Get-WinEvent -FilterXml $filter | Sort-Object TimeCreated |
      Select-Object TimeCreated, Id, Message | ForEach-Object {
        $type = switch ($_.Id) {
          6005 { "Boot (EventID 6005 - Event Log Started)" }
          6006 { "Shutdown (EventID 6006 - Event Log Stopped)" }
          default { "Other" }
        }
        "{0}`t{1}" -f $_.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss"), $type
      }
  '
}

main() {
  echo "Boot and Shutdown Events for the Last 7 Days:"
  echo -e "Timestamp\t\tType"
  bootlog::get_event_log_data
}

main "$@"
