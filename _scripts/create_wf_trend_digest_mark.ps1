Add-Type -AssemblyName System.Security
$datPath = Join-Path $env:LOCALAPPDATA 'lp-secrets\n8n-api-key.dat'
$encrypted = [System.IO.File]::ReadAllBytes($datPath)
$bytes = [System.Security.Cryptography.ProtectedData]::Unprotect($encrypted, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
$apiKey = [System.Text.Encoding]::UTF8.GetString($bytes)
$base = 'https://logosandpathos.app.n8n.cloud/api/v1'

# Notion Header Auth credential id (httpHeaderAuth)
$notionHeaderAuthId = 'b15baqfC1ToiS43R'
# Notion DB ID for articles
$articlesDbId = '0cc209e3-2016-4969-9b46-38e7e16adf3b'

$validateCode = @"
const body = `$input.first().json.body;
let payload;
try { payload = (typeof body === 'string') ? JSON.parse(body) : body; } catch (e) { payload = null; }
if (!payload) return [{ json: { ok: false, error: 'invalid body' } }];
const page_id = payload.page_id;
const important = payload.important;
if (!page_id || typeof important !== 'boolean') {
  return [{ json: { ok: false, error: 'page_id required and important must be bool' } }];
}
const normalized = String(page_id).replace(/-/g, '');
if (normalized.length !== 32 || !/^[0-9a-f]+`$/i.test(normalized)) {
  return [{ json: { ok: false, error: 'invalid page_id format' } }];
}
return [{ json: { ok: true, page_id, important } }];
"@

$jsonBodyExpr = '={ "properties": { "重要": { "checkbox": {{ $json.important }} } } }'

$wf = @{
  name = 'wf-trend-digest-mark'
  settings = @{
    executionOrder = 'v1'
    saveDataErrorExecution = 'all'
    saveDataSuccessExecution = 'all'
    saveExecutionProgress = $true
    saveManualExecutions = $true
  }
  nodes = @(
    @{
      parameters = @{
        httpMethod = 'POST'
        path = 'trend-digest-mark'
        responseMode = 'responseNode'
        options = @{}
      }
      id = '11111111-1111-1111-1111-111111111111'
      name = 'Webhook'
      type = 'n8n-nodes-base.webhook'
      typeVersion = 2
      position = @(240, 300)
      webhookId = 'tdg-mark-9c9d7a'
    }
    @{
      parameters = @{
        language = 'javaScript'
        jsCode = $validateCode
      }
      id = '22222222-2222-2222-2222-222222222222'
      name = 'Validate'
      type = 'n8n-nodes-base.code'
      typeVersion = 2
      position = @(440, 300)
    }
    @{
      parameters = @{
        conditions = @{
          options = @{ caseSensitive = $true; leftValue = ''; typeValidation = 'strict' }
          conditions = @(
            @{
              id = 'cond-ok'
              leftValue = '={{ $json.ok }}'
              rightValue = $true
              operator = @{ type = 'boolean'; operation = 'true'; singleValue = $true }
            }
          )
          combinator = 'and'
        }
        options = @{}
      }
      id = '33333333-3333-3333-3333-333333333333'
      name = 'IF ok'
      type = 'n8n-nodes-base.if'
      typeVersion = 2
      position = @(640, 300)
    }
    @{
      parameters = @{
        method = 'PATCH'
        url = '=https://api.notion.com/v1/pages/{{ $json.page_id }}'
        authentication = 'predefinedCredentialType'
        nodeCredentialType = 'httpHeaderAuth'
        sendHeaders = $true
        headerParameters = @{
          parameters = @(
            @{ name = 'Notion-Version'; value = '2022-06-28' }
            @{ name = 'Content-Type'; value = 'application/json' }
          )
        }
        sendBody = $true
        specifyBody = 'json'
        jsonBody = $jsonBodyExpr
        options = @{}
      }
      id = '44444444-4444-4444-4444-444444444444'
      name = 'Notion PATCH'
      type = 'n8n-nodes-base.httpRequest'
      typeVersion = 4.2
      position = @(840, 200)
      credentials = @{
        httpHeaderAuth = @{
          id = $notionHeaderAuthId
          name = 'Notion Header Auth'
        }
      }
    }
    @{
      parameters = @{
        respondWith = 'text'
        responseBody = 'ok'
        options = @{
          responseHeaders = @{
            entries = @(
              @{ name = 'Access-Control-Allow-Origin'; value = '*' }
              @{ name = 'Content-Type'; value = 'text/plain; charset=utf-8' }
            )
          }
        }
      }
      id = '55555555-5555-5555-5555-555555555555'
      name = 'Respond 200'
      type = 'n8n-nodes-base.respondToWebhook'
      typeVersion = 1
      position = @(1040, 200)
    }
    @{
      parameters = @{
        respondWith = 'text'
        responseBody = '=invalid: {{ $json.error }}'
        options = @{
          responseCode = 400
          responseHeaders = @{
            entries = @(
              @{ name = 'Access-Control-Allow-Origin'; value = '*' }
              @{ name = 'Content-Type'; value = 'text/plain; charset=utf-8' }
            )
          }
        }
      }
      id = '66666666-6666-6666-6666-666666666666'
      name = 'Respond 400'
      type = 'n8n-nodes-base.respondToWebhook'
      typeVersion = 1
      position = @(840, 400)
    }
  )
  connections = @{
    Webhook = @{
      main = @(, @(@{ node = 'Validate'; type = 'main'; index = 0 }))
    }
    Validate = @{
      main = @(, @(@{ node = 'IF ok'; type = 'main'; index = 0 }))
    }
    'IF ok' = @{
      main = @(
        , @(@{ node = 'Notion PATCH'; type = 'main'; index = 0 }),
        , @(@{ node = 'Respond 400'; type = 'main'; index = 0 })
      )
    }
    'Notion PATCH' = @{
      main = @(, @(@{ node = 'Respond 200'; type = 'main'; index = 0 }))
    }
  }
}

$json = $wf | ConvertTo-Json -Depth 30 -Compress
[System.IO.File]::WriteAllText("$PSScriptRoot\..\_tmp\wf_mark_create.json", $json, [System.Text.UTF8Encoding]::new($false))
"--- preview JSON head ---"
$json.Substring(0, [Math]::Min(400, $json.Length))
""
"--- POST /workflows ---"
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($json)
try {
  $r = Invoke-RestMethod -Method Post -Uri "$base/workflows" -Headers @{ 'X-N8N-API-KEY' = $apiKey; 'Content-Type' = 'application/json' } -Body $bodyBytes
  "created: id=$($r.id)  active=$($r.active)"
  "Save id for next step: $($r.id)"
} catch {
  $err = $_.Exception.Response
  if ($err) {
    $sr = New-Object System.IO.StreamReader($err.GetResponseStream())
    $errBody = $sr.ReadToEnd()
    "HTTP $($err.StatusCode): $errBody"
  } else {
    "Error: $_"
  }
}
