FROM nginx:1.20.2

USER root

COPY dist/spa/ /usr/share/nginx/html
COPY nginx.template.conf /etc/nginx/nginx.conf
