%global debug_package %{nil}

Name: docker-ce-cli
Version: %{_version}
Release: %{_release}%{?dist}
Epoch: 1
Summary: The open-source application container engine
Group: Tools/Docker
License: ASL 2.0
Source0: cli.tgz
Source1: plugin-installers.tgz
URL: https://www.docker.com
Vendor: Docker
Packager: Docker <support@docker.com>

# required packages on install
Requires: /bin/sh
Requires: /usr/sbin/groupadd
# TODO change once we support scan-plugin on other architectures
%ifarch x86_64
Requires: docker-scan-plugin(x86-64)
%endif

BuildRequires: make
BuildRequires: libtool-ltdl-devel
BuildRequires: git

# conflicting packages
Conflicts: docker
Conflicts: docker-io
Conflicts: docker-engine-cs
Conflicts: docker-ee
Conflicts: docker-ee-cli

%description
Docker is is a product for you to build, ship and run any application as a
lightweight container.

Docker containers are both hardware-agnostic and platform-agnostic. This means
they can run anywhere, from your laptop to the largest cloud compute instance
and everything in between - and they don't require you to use a particular
language, framework or packaging system. That makes them great building blocks
for deploying and scaling web apps, databases, and backend services without
depending on a particular stack or provider.

%prep
%setup -q -c -n src -a 1

%build
mkdir -p /go/src/github.com/docker
rm -f /go/src/github.com/docker/cli
ln -s ${RPM_BUILD_DIR}/src/cli /go/src/github.com/docker/cli
pushd /go/src/github.com/docker/cli
VERSION=%{_origversion} GITCOMMIT=%{_gitcommit_cli} GO_LINKMODE=dynamic ./scripts/build/binary && DISABLE_WARN_OUTSIDE_CONTAINER=1 make manpages # cli
popd

# Build all associated plugins
pushd ${RPM_BUILD_DIR}/src/plugins
for installer in *.installer; do
    if [ "${installer}" != "scan.installer" ]; then
        bash ${installer} build
    fi
done
popd


%check
ver="$(cli/build/docker --version)"; \
    test "$ver" = "Docker version %{_origversion}, build %{_gitcommit_cli}" && echo "PASS: cli version OK" || (echo "FAIL: cli version ($ver) did not match" && exit 1)

%install
# install binary
install -d ${RPM_BUILD_ROOT}%{_bindir}
install -p -m 755 cli/build/docker ${RPM_BUILD_ROOT}%{_bindir}/docker

# install plugins
pushd ${RPM_BUILD_DIR}/src/plugins
for installer in *.installer; do
    if [ "${installer}" != "scan.installer" ]; then
        DESTDIR=${RPM_BUILD_ROOT} \
        PREFIX=%{_libexecdir}/docker/cli-plugins \
        bash ${installer} install_plugin
    fi
done
popd

# add bash, zsh, and fish completions
install -d ${RPM_BUILD_ROOT}%{_datadir}/bash-completion/completions
install -d ${RPM_BUILD_ROOT}%{_datadir}/zsh/vendor-completions
install -d ${RPM_BUILD_ROOT}%{_datadir}/fish/vendor_completions.d
install -p -m 644 cli/contrib/completion/bash/docker ${RPM_BUILD_ROOT}%{_datadir}/bash-completion/completions/docker
install -p -m 644 cli/contrib/completion/zsh/_docker ${RPM_BUILD_ROOT}%{_datadir}/zsh/vendor-completions/_docker
install -p -m 644 cli/contrib/completion/fish/docker.fish ${RPM_BUILD_ROOT}%{_datadir}/fish/vendor_completions.d/docker.fish

# install manpages
install -d ${RPM_BUILD_ROOT}%{_mandir}/man1
install -p -m 644 cli/man/man1/*.1 ${RPM_BUILD_ROOT}%{_mandir}/man1
install -d ${RPM_BUILD_ROOT}%{_mandir}/man5
install -p -m 644 cli/man/man5/*.5 ${RPM_BUILD_ROOT}%{_mandir}/man5
install -d ${RPM_BUILD_ROOT}%{_mandir}/man8
install -p -m 644 cli/man/man8/*.8 ${RPM_BUILD_ROOT}%{_mandir}/man8

mkdir -p build-docs
for cli_file in LICENSE MAINTAINERS NOTICE README.md; do
    cp "cli/$cli_file" "build-docs/$cli_file"
done

# list files owned by the package here
%files
%doc build-docs/LICENSE build-docs/MAINTAINERS build-docs/NOTICE build-docs/README.md
%{_bindir}/docker
%{_libexecdir}/docker/cli-plugins/*
%{_datadir}/bash-completion/completions/docker
%{_datadir}/zsh/vendor-completions/_docker
%{_datadir}/fish/vendor_completions.d/docker.fish
%doc
%{_mandir}/man1/*
%{_mandir}/man5/*
%{_mandir}/man8/*


%post
if ! getent group docker > /dev/null; then
    groupadd --system docker
fi

%changelog
