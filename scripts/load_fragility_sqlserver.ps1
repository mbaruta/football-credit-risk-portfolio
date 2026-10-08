param(
    [string]$Server = 'localhost\SQLEXPRESS',
    [string]$Database = 'football_credit_risk',
    [string]$CsvPath = ''
)
$ErrorActionPreference = 'Stop'

# Run SQL/01_create_financial_fragility_table.sql before this script.
# Run SQL/02_create_dashboard_view.sql after this script.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $CsvPath) { $CsvPath = Join-Path $repoRoot 'data\processed\financial_fragility_scores.csv' }
if (-not (Test-Path $CsvPath)) { throw "Missing generated CSV: $CsvPath" }

$rows = @(Import-Csv -Path $CsvPath -Encoding UTF8)
if (-not $rows.Count) { throw 'The generated CSV has no data.' }

$numericColumns = @(
    'cash', 'current_assets', 'total_assets', 'current_liabilities',
    'total_liabilities', 'equity', 'net_result', 'current_liquidity',
    'liability_ratio', 'return_on_assets', 'liquidity_risk',
    'solvency_risk', 'profitability_risk', 'financial_fragility_score',
    'previous_loss_rate'
)
$expected = @('club','fiscal_year','cash','current_assets','total_assets',
    'current_liabilities','total_liabilities','equity','net_result',
    'current_liquidity','liability_ratio','return_on_assets','negative_equity',
    'liquidity_risk','solvency_risk','profitability_risk',
    'financial_fragility_score','previous_loss_rate')
$actual = @($rows[0].PSObject.Properties.Name)
if (($expected -join ',') -ne ($actual -join ',')) {
    throw "Unexpected CSV schema. Expected: $($expected -join ',') / Found: $($actual -join ',')"
}

$table = New-Object System.Data.DataTable
[void]$table.Columns.Add('club', [string])
[void]$table.Columns.Add('fiscal_year', [int])
foreach ($name in $expected) {
    if ($numericColumns -contains $name) { [void]$table.Columns.Add($name, [decimal]) }
}
[void]$table.Columns.Add('negative_equity', [bool])
$table.Columns['club'].SetOrdinal(0)
$table.Columns['fiscal_year'].SetOrdinal(1)
foreach ($name in $expected) { $table.Columns[$name].SetOrdinal([array]::IndexOf($expected, $name)) }

foreach ($r in $rows) {
    $data = $table.NewRow()
    foreach ($name in $expected) {
        $value = [string]$r.$name
        if ($name -eq 'club') { $data[$name] = $value }
        elseif ($name -eq 'fiscal_year') { $data[$name] = [int]::Parse($value) }
        elseif ($name -eq 'negative_equity') { $data[$name] = ($value -eq '1') }
        elseif ($value -eq '' -and $name -eq 'previous_loss_rate') {
            $data[$name] = [DBNull]::Value
        }
        else {
            $data[$name] = [decimal]::Parse(
                $value,
                [Globalization.NumberStyles]::Float,
                [Globalization.CultureInfo]::InvariantCulture
            )
        }
    }
    $table.Rows.Add($data)
}

$connectionString = "Server=$Server;Database=$Database;Integrated Security=true;TrustServerCertificate=true;"
$connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
$connection.Open()
$transaction = $connection.BeginTransaction()
try {
    $cmd = $connection.CreateCommand()
    $cmd.Transaction = $transaction
    $cmd.CommandText = 'DELETE FROM dbo.financial_fragility_scores;'
    [void]$cmd.ExecuteNonQuery()

    $bulk = [System.Data.SqlClient.SqlBulkCopy]::new(
        $connection,
        [System.Data.SqlClient.SqlBulkCopyOptions]::Default,
        $transaction
    )
    $bulk.DestinationTableName = 'dbo.financial_fragility_scores'
    foreach ($name in $expected) { [void]$bulk.ColumnMappings.Add($name, $name) }
    $bulk.BatchSize = 100
    $bulk.WriteToServer($table)
    $bulk.Close()

    $cmd.CommandText = 'SELECT COUNT(*) FROM dbo.financial_fragility_scores;'
    $n = [int]$cmd.ExecuteScalar()
    if ($n -ne $rows.Count) { throw "Import count mismatch: $n instead of $($rows.Count)" }
    $cmd.CommandText = @'
SELECT COUNT(*) FROM dbo.financial_fragility_scores
WHERE ABS(total_assets - total_liabilities - equity) > 1
   OR financial_fragility_score < 0 OR financial_fragility_score > 100;
'@
    $invalid = [int]$cmd.ExecuteScalar()
    if ($invalid -ne 0) { throw "SQL data validation failed for $invalid rows" }

    $transaction.Commit()
    Write-Host "SQL Server import verified: $n rows, $Server, $Database"
}
catch {
    try { $transaction.Rollback() } catch {}
    throw
}
finally { $connection.Close() }
