from mattdm/fedora:f20

# make sure the package repository is up to date
add resources/fedora.repo /etc/yum.repos.d/fedora.repo
add resources/fedora-updates.repo /etc/yum.repos.d/fedora-updates.repo

run useradd sandbox
run yum -y update && yum -y install zeroinstall-injector && yum clean all
run yum install -y PackageKit
run yum install -y python3
run yum install -y strace
run yum install -y gpg
run yum install -y ocaml
run yum install -y ncurses-devel
run yum install -y m4
run yum install -y ocaml-camlp4-devel
run yum install -y gcc-c++
run yum install -y python-devel python3-devel
run yum install -y libffi-devel
run yum install -y openssl-devel
run yum install -y gtksourceview2-devel
run yum install -y which
# required for 0compile-python3; which is required for SNI ssl support
run yum install -y python3-gobject
