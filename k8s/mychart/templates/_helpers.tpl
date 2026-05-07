{{/*
Expand the name of the chart.
*/}}
{{- define "mychart.name" -}}
{{- include "common.name" . -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mychart.fullname" -}}
{{- include "common.fullname" . -}}
{{- end -}}

{{/*
Create chart label.
*/}}
{{- define "mychart.chart" -}}
{{- include "common.chart" . -}}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "mychart.selectorLabels" -}}
{{ include "common.selectorLabels" . }}
{{- end -}}

{{/*
Common labels.
*/}}
{{- define "mychart.labels" -}}
{{ include "common.labels" . }}
{{- end -}}

{{/*
Service account name.
*/}}
{{- define "mychart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "mychart.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Secret name.
*/}}
{{- define "mychart.secretName" -}}
{{- if .Values.secrets.nameOverride -}}
{{- .Values.secrets.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-secret" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
ConfigMap name for file-based application configuration.
*/}}
{{- define "mychart.configMapName" -}}
{{- printf "%s-config" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
ConfigMap name for environment variable injection.
*/}}
{{- define "mychart.envConfigMapName" -}}
{{- printf "%s-env" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
PVC/PV name for persistent application data.
*/}}
{{- define "mychart.dataName" -}}
{{- printf "%s-data" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Preview service name for blue-green rollouts.
*/}}
{{- define "mychart.previewServiceName" -}}
{{- printf "%s-preview" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Headless service name for StatefulSet pod DNS.
*/}}
{{- define "mychart.headlessServiceName" -}}
{{- printf "%s-headless" (include "mychart.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Named template for regular environment variables.
*/}}
{{- define "mychart.envVars" -}}
{{- range .Values.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
{{- end -}}

{{/*
Vault injector annotations.
*/}}
{{- define "mychart.vaultAnnotations" -}}
vault.hashicorp.com/agent-inject: {{ .Values.vault.agent.inject | quote }}
vault.hashicorp.com/role: {{ .Values.vault.role | quote }}
vault.hashicorp.com/auth-path: {{ .Values.vault.authPath | quote }}
vault.hashicorp.com/agent-inject-secret-{{ .Values.vault.injectFilename }}: {{ .Values.vault.secretPath | quote }}
{{- if .Values.vault.agent.prePopulateOnly }}
vault.hashicorp.com/agent-pre-populate-only: "true"
{{- end }}
{{- if .Values.vault.agent.template.enabled }}
vault.hashicorp.com/agent-inject-template-{{ .Values.vault.agent.template.filename }}: |
  {{`{{- with secret "`}}{{ .Values.vault.agent.template.path }}{{`" -}}`}}
  USERNAME={{`{{ .Data.data.username }}`}}
  PASSWORD={{`{{ .Data.data.password }}`}}
  {{`{{- end }}`}}
{{- end }}
{{- end -}}
