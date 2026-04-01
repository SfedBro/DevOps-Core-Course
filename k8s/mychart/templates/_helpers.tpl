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
