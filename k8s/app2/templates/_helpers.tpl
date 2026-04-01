{{/*
Compatibility wrappers around the shared common-lib helpers.
*/}}
{{- define "app2.name" -}}
{{- include "common.name" . -}}
{{- end -}}

{{- define "app2.fullname" -}}
{{- include "common.fullname" . -}}
{{- end -}}

{{- define "app2.chart" -}}
{{- include "common.chart" . -}}
{{- end -}}

{{- define "app2.selectorLabels" -}}
{{ include "common.selectorLabels" . }}
{{- end -}}

{{- define "app2.labels" -}}
{{ include "common.labels" . }}
{{- end -}}
