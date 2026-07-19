{{- define "openmaster.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- define "openmaster.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "openmaster.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- define "openmaster.labels" -}}
app.kubernetes.io/name: {{ include "openmaster.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: openmaster
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
{{- define "openmaster.image" -}}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.repository .Values.image.tag }}
{{- end }}
{{- define "openmaster.secretName" -}}
{{- required "externalSecrets.existingSecretName is required" .Values.externalSecrets.existingSecretName -}}
{{- end }}
{{- define "openmaster.componentLabels" -}}
{{ include "openmaster.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
{{- define "openmaster.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openmaster.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
