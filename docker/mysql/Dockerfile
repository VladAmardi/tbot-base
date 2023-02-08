FROM percona:5.7-centos

USER root
RUN cd /etc/yum.repos.d/ && \
    sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-* && \
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*
RUN yum -y update && \
    yum -y install percona-toolkit less
RUN yum -y reinstall procps
RUN mv /etc/localtime /etc/localtime.backup
#wget https://raw.githubusercontent.com/major/MySQLTuner-perl/master/mysqltuner.pl
RUN ln -s /usr/share/zoneinfo/Europe/Kiev /etc/localtime
COPY mysqld.cnf /etc/percona-server.conf.d/mysqld.cnf
COPY init.sql /docker-entrypoint-initdb.d/init.sql
RUN chmod -R 777 /docker-entrypoint-initdb.d
USER mysql
CMD ["mysqld"]
