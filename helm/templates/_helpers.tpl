{{/*
Resolve a container image reference.

Uses backend.image.repository (full repo path) when set; otherwise composes
registry/name:tag from global.registry, image.name, and image.tag / global.imageTag.
*/}}
{{- define "supply-chain.containerImage" -}}
{{- $image := .image -}}
{{- $global := .global -}}
{{- if $image.repository -}}
{{- printf "%s:%s" $image.repository ($image.tag | default ($global.imageTag | default "latest")) -}}
{{- else -}}
{{- $registry := $global.registry | default "quay.io/rh-ai-quickstart" -}}
{{- $tag := $image.tag | default ($global.imageTag | default "latest") -}}
{{- $name := required "image.name is required when image.repository is unset" $image.name -}}
{{- printf "%s/%s:%s" $registry $name $tag -}}
{{- end -}}
{{- end -}}
