%define	with_python_subpackage	1%{nil}
%define	with_python_version	2.3%{nil}
%define	with_bzip2		1%{nil}
%define	with_apidocs		1%{nil}

# XXX legacy requires './' payload prefix to be omitted from rpm packages.
%define	_noPayloadPrefix	1

%define	__prefix	/usr
%{?!_lib: %define _lib lib}
%{expand: %%define __share %(if [ -d %{__prefix}/share/man ]; then echo /share ; else echo %%{nil} ; fi)}

%define __bindir	%{__prefix}/bin
%define __includedir	%{__prefix}/include
%define __libdir	%{__prefix}/%{_lib}
%define __mandir	%{__prefix}%{__share}/man

Summary: The RPM package management system.
Name: rpm
%define version 4.3.2
Version: %{version}
%{expand: %%define rpm_version %{version}}
Release: 5
Group: System Environment/Base
Source: ftp://ftp.rpm.org/pub/rpm/dist/rpm-4.0.x/rpm-%{rpm_version}.tar.gz
License: GPL
Conflicts: patch < 2.5
%ifos linux
Prereq: fileutils shadow-utils
%endif
Requires: popt = 1.9.1
Obsoletes: rpm-perl < %{version}

# XXX necessary only to drag in /usr/lib/libelf.a, otherwise internal elfutils.
BuildRequires: elfutils-libelf
BuildRequires: elfutils-devel

BuildRequires: zlib-devel

BuildRequires: beecrypt-devel >= 3.0.1
Requires: beecrypt >= 3.0.1

# XXX Red Hat 5.2 has not bzip2 or python
%if %{with_bzip2}
BuildRequires: bzip2 >= 0.9.0c-2
%endif
%if %{with_python_subpackage}
BuildRequires: python-devel >= %{with_python_version}
%endif

BuildRoot: %{_tmppath}/%{name}-root

%description
The RPM Package Manager (RPM) is a powerful command line driven
package management system capable of installing, uninstalling,
verifying, querying, and updating software packages. Each software
package consists of an archive of files along with information about
the package like its version, a description, etc.

%package libs
Summary:  Libraries for manipulating RPM packages.
Group: Development/Libraries

%description libs
This package contains the RPM shared libraries.

%package devel
Summary:  Development files for manipulating RPM packages.
Group: Development/Libraries
Requires: rpm = %{rpm_version}-%{release}

%description devel
This package contains the RPM C library and header files. These
development files will simplify the process of writing programs that
manipulate RPM packages and databases. These files are intended to
simplify the process of creating graphical package managers or any
other tools that need an intimate knowledge of RPM packages in order
to function.

This package should be installed if you want to develop programs that
will manipulate RPM packages and databases.

%package build
Summary: Scripts and executable programs used to build packages.
Group: Development/Tools
Requires: rpm = %{rpm_version}-%{release}, patch >= 2.5, file
Provides: rpmbuild(VendorConfig) = 4.1-1

%description build
The rpm-build package contains the scripts and executable programs
that are used to build packages using the RPM Package Manager.

%if %{with_python_subpackage}
%package python
Summary: Python bindings for apps which will manipulate RPM packages.
Group: Development/Libraries
Requires: rpm = %{rpm_version}-%{release}
Requires: python >= %{with_python_version}
Requires: elfutils >= 0.55

%description python
The rpm-python package contains a module that permits applications
written in the Python programming language to use the interface
supplied by RPM Package Manager libraries.

This package should be installed if you want to develop Python
programs that will manipulate RPM packages and databases.
%endif

%package -n popt
Summary: A C library for parsing command line parameters.
Group: Development/Libraries
Version: 1.9.1

%description -n popt
Popt is a C library for parsing command line parameters. Popt was
heavily influenced by the getopt() and getopt_long() functions, but it
improves on them by allowing more powerful argument expansion. Popt
can parse arbitrary argv[] style arrays and automatically set
variables based on command line arguments. Popt allows command line
arguments to be aliased via configuration files and includes utility
functions for parsing arbitrary strings into argv[] arrays using
shell-like rules.

%prep
%setup -q

%build

# XXX rpm needs functioning nptl for configure tests
unset LD_ASSUME_KERNEL || :

%if %{with_python_subpackage}
WITH_PYTHON="--with-python=%{with_python_version}"
%else
WITH_PYTHON="--without-python"
%endif

%ifos linux
CFLAGS="$RPM_OPT_FLAGS"; export CFLAGS
./configure --prefix=%{__prefix} --sysconfdir=/etc \
	--localstatedir=/var --infodir='${prefix}%{__share}/info' \
	--mandir='${prefix}%{__share}/man' \
	$WITH_PYTHON --enable-posixmutexes --without-javaglue
%else
CFLAGS="$RPM_OPT_FLAGS" ./configure --prefix=%{__prefix} $WITH_PYTHON \
	--without-javaglue
%endif

make %{_smp_mflags}

%install
# XXX rpm needs functioning nptl for configure tests
unset LD_ASSUME_KERNEL || :

rm -rf $RPM_BUILD_ROOT

make DESTDIR="$RPM_BUILD_ROOT" install

%ifos linux

# Save list of packages through cron
mkdir -p ${RPM_BUILD_ROOT}/etc/cron.daily
install -m 755 scripts/rpm.daily ${RPM_BUILD_ROOT}/etc/cron.daily/rpm

mkdir -p ${RPM_BUILD_ROOT}/etc/logrotate.d
install -m 644 scripts/rpm.log ${RPM_BUILD_ROOT}/etc/logrotate.d/rpm

mkdir -p $RPM_BUILD_ROOT/etc/rpm

mkdir -p $RPM_BUILD_ROOT/var/spool/repackage
mkdir -p $RPM_BUILD_ROOT/var/lib/rpm
for dbi in \
	Basenames Conflictname Dirnames Group Installtid Name Packages \
	Providename Provideversion Requirename Requireversion Triggername \
	Filemd5s Pubkeys Sha1header Sigmd5 \
	__db.001 __db.002 __db.003 __db.004 __db.005 __db.006 __db.007 \
	__db.008 __db.009
do
    touch $RPM_BUILD_ROOT/var/lib/rpm/$dbi
done

# - serialize rpmtsRun() using fcntl on /var/lock/rpm/transaction.
mkdir -p ${RPM_BUILD_ROOT}/var/lock/rpm
%endif

%if %{with_apidocs}
gzip -9n apidocs/man/man*/* || :
%endif

# Get rid of unpackaged files
{ cd $RPM_BUILD_ROOT
  rm -rf .%{__includedir}/beecrypt
  rm -f .%{__libdir}/libbeecrypt.{a,la,so.2.2.0}
  rm -f .%{__prefix}/lib/rpm/{Specfile.pm,cpanflute,cpanflute2,rpmdiff,rpmdiff.cgi,sql.prov,sql.req,tcl.req}
  rm -rf .%{__mandir}/{fr,ko}
}

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%ifos linux
if [ -f /var/lib/rpm/packages.rpm ]; then
    echo "
You have (unsupported)
	/var/lib/rpm/packages.rpm	db1 format installed package headers
Please install rpm-4.0.4 first, and do
	rpm --rebuilddb
to convert your database from db1 to db3 format.
"
    exit 1
fi
/usr/sbin/groupadd -g 37 rpm				> /dev/null 2>&1
/usr/sbin/useradd  -r -d /var/lib/rpm -u 37 -g 37 rpm -s /sbin/nologin	> /dev/null 2>&1
%endif
exit 0

%post
%ifos linux
/sbin/ldconfig

# Establish correct rpmdb ownership.
/bin/chown rpm.rpm /var/lib/rpm/[A-Z]*

# XXX Detect (and remove) incompatible dbenv files during db-4.2.52 upgrade.
# XXX Removing dbenv files in %%post opens a lock race window, a tolerable
# XXX risk compared to the support issues involved with upgrading Berkeley DB.
[ -w /var/lib/rpm/__db.001 ] &&
/usr/lib/rpm/rpmdb_stat -CA -h /var/lib/rpm 2>&1 |
grep "db_stat: Program version 4.2 doesn't match environment version" 2>&1 > /dev/null &&
	rm -f /var/lib/rpm/__db*
                                                                                
%endif
exit 0

%ifos linux
%postun
/sbin/ldconfig
if [ $1 = 0 ]; then
    /usr/sbin/userdel rpm
    /usr/sbin/groupdel rpm
fi
exit 0

%post devel -p /sbin/ldconfig
%postun devel -p /sbin/ldconfig

%post -n popt -p /sbin/ldconfig
%postun -n popt -p /sbin/ldconfig
%endif

%if %{with_python_subpackage}
%post python -p /sbin/ldconfig
%postun python -p /sbin/ldconfig
%endif

%define	rpmattr		%attr(0755, rpm, rpm)

%files
%defattr(-,root,root)
%doc RPM-PGP-KEY RPM-GPG-KEY BETA-GPG-KEY CHANGES GROUPS doc/manual/[a-z]*
# XXX comment these lines out if building with rpm that knows not %pubkey attr
%pubkey RPM-PGP-KEY
%pubkey RPM-GPG-KEY
%pubkey BETA-GPG-KEY
%attr(0755, rpm, rpm)	/bin/rpm

%ifos linux
%config(noreplace,missingok)	/etc/cron.daily/rpm
%config(noreplace,missingok)	/etc/logrotate.d/rpm
%dir				/etc/rpm
#%config(noreplace,missingok)	/etc/rpm/macros.*
%attr(0755, rpm, rpm)	%dir /var/lib/rpm
%attr(0755, rpm, rpm)	%dir /var/spool/repackage
%attr(0755, rpm, rpm)	%dir /var/lock/rpm

%define	rpmdbattr %attr(0644, rpm, rpm) %verify(not md5 size mtime) %ghost %config(missingok,noreplace)
%rpmdbattr	/var/lib/rpm/*
%endif

%rpmattr	%{__bindir}/rpm2cpio
%rpmattr	%{__bindir}/gendiff
%rpmattr	%{__bindir}/rpmdb
#%rpmattr	%{__bindir}/rpm[eiu]
%rpmattr	%{__bindir}/rpmsign
%rpmattr	%{__bindir}/rpmquery
%rpmattr	%{__bindir}/rpmverify

%attr(0755, rpm, rpm)	%dir %{__prefix}/lib/rpm
%rpmattr	%{__prefix}/lib/rpm/config.guess
%rpmattr	%{__prefix}/lib/rpm/config.sub
%rpmattr	%{__prefix}/lib/rpm/convertrpmrc.sh
%attr(0644, rpm, rpm)	%{__prefix}/lib/rpm/macros
%rpmattr	%{__prefix}/lib/rpm/mkinstalldirs
%rpmattr	%{__prefix}/lib/rpm/rpm.*
%rpmattr	%{__prefix}/lib/rpm/rpm2cpio.sh
%rpmattr	%{__prefix}/lib/rpm/rpm[deiukqv]
%rpmattr	%{__prefix}/lib/rpm/tgpg
%attr(0644, rpm, rpm)	%{__prefix}/lib/rpm/rpmpopt*
%attr(0644, rpm, rpm)	%{__prefix}/lib/rpm/rpmrc

%ifarch i386 i486 i586 i686 athlon
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/i[3456]86*
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/athlon*
%endif
%ifarch alpha alphaev5 alphaev56 alphapca56 alphaev6 alphaev67
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/alpha*
%endif
%ifarch sparc sparcv8 sparcv9 sparc64
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/sparc*
%endif
%ifarch ia64
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/ia64*
%endif
%ifarch powerpc ppc ppciseries ppcpseries ppcmac ppc64
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/ppc*
%endif
%ifarch s390 s390x
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/s390*
%endif
%ifarch armv3l armv4l
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/armv[34][lb]*
%endif
%ifarch mips mipsel
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/mips*
%endif
%ifarch x86_64
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/x86_64*
%endif
%attr(-, rpm, rpm)		%{__prefix}/lib/rpm/noarch*

%rpmattr	%{__prefix}/lib/rpm/rpmdb_deadlock
%rpmattr	%{__prefix}/lib/rpm/rpmdb_dump
%rpmattr	%{__prefix}/lib/rpm/rpmdb_load
%rpmattr	%{__prefix}/lib/rpm/rpmdb_loadcvt
%rpmattr	%{__prefix}/lib/rpm/rpmdb_svc
%rpmattr	%{__prefix}/lib/rpm/rpmdb_stat
%rpmattr	%{__prefix}/lib/rpm/rpmdb_verify
%rpmattr	%{__prefix}/lib/rpm/rpmfile

%lang(cs)	%{__prefix}/*/locale/cs/LC_MESSAGES/rpm.mo
%lang(da)	%{__prefix}/*/locale/da/LC_MESSAGES/rpm.mo
%lang(de)	%{__prefix}/*/locale/de/LC_MESSAGES/rpm.mo
%lang(fi)	%{__prefix}/*/locale/fi/LC_MESSAGES/rpm.mo
%lang(fr)	%{__prefix}/*/locale/fr/LC_MESSAGES/rpm.mo
%lang(gl)	%{__prefix}/*/locale/gl/LC_MESSAGES/rpm.mo
%lang(is)	%{__prefix}/*/locale/is/LC_MESSAGES/rpm.mo
%lang(ja)	%{__prefix}/*/locale/ja/LC_MESSAGES/rpm.mo
%lang(ko)	%{__prefix}/*/locale/ko/LC_MESSAGES/rpm.mo
%lang(no)	%{__prefix}/*/locale/no/LC_MESSAGES/rpm.mo
%lang(pl)	%{__prefix}/*/locale/pl/LC_MESSAGES/rpm.mo
%lang(pt)	%{__prefix}/*/locale/pt/LC_MESSAGES/rpm.mo
%lang(pt_BR)	%{__prefix}/*/locale/pt_BR/LC_MESSAGES/rpm.mo
%lang(ro)	%{__prefix}/*/locale/ro/LC_MESSAGES/rpm.mo
%lang(ru)	%{__prefix}/*/locale/ru/LC_MESSAGES/rpm.mo
%lang(sk)	%{__prefix}/*/locale/sk/LC_MESSAGES/rpm.mo
%lang(sl)	%{__prefix}/*/locale/sl/LC_MESSAGES/rpm.mo
%lang(sr)	%{__prefix}/*/locale/sr/LC_MESSAGES/rpm.mo
%lang(sv)	%{__prefix}/*/locale/sv/LC_MESSAGES/rpm.mo
%lang(tr)	%{__prefix}/*/locale/tr/LC_MESSAGES/rpm.mo

%{__mandir}/man1/gendiff.1*
%{__mandir}/man8/rpm.8*
%{__mandir}/man8/rpm2cpio.8*
%lang(ja)	%{__mandir}/ja/man[18]/*.[18]*
%lang(pl)	%{__mandir}/pl/man[18]/*.[18]*
%lang(ru)	%{__mandir}/ru/man[18]/*.[18]*
%lang(sk)	%{__mandir}/sk/man[18]/*.[18]*

%files libs
%defattr(-,root,root)
%{__libdir}/librpm-4.3.so
%{__libdir}/librpmdb-4.3.so
%{__libdir}/librpmio-4.3.so
%{__libdir}/librpmbuild-4.3.so

%files build
%defattr(-,root,root)
%dir %{__prefix}/src/redhat
%dir %{__prefix}/src/redhat/BUILD
%dir %{__prefix}/src/redhat/SPECS
%dir %{__prefix}/src/redhat/SOURCES
%dir %{__prefix}/src/redhat/SRPMS
%dir %{__prefix}/src/redhat/RPMS
%{__prefix}/src/redhat/RPMS/*
%rpmattr	%{__bindir}/rpmbuild
%rpmattr	%{__prefix}/lib/rpm/brp-*
%rpmattr	%{__prefix}/lib/rpm/check-files
%rpmattr	%{__prefix}/lib/rpm/check-prereqs
%rpmattr	%{__prefix}/lib/rpm/config.site
%rpmattr	%{__prefix}/lib/rpm/cross-build
%rpmattr	%{__prefix}/lib/rpm/debugedit
%rpmattr	%{__prefix}/lib/rpm/find-debuginfo.sh
%rpmattr	%{__prefix}/lib/rpm/find-lang.sh
%rpmattr	%{__prefix}/lib/rpm/find-prov.pl
%rpmattr	%{__prefix}/lib/rpm/find-provides
%rpmattr	%{__prefix}/lib/rpm/find-provides.perl
%rpmattr	%{__prefix}/lib/rpm/find-req.pl
%rpmattr	%{__prefix}/lib/rpm/find-requires
%rpmattr	%{__prefix}/lib/rpm/find-requires.perl
%rpmattr	%{__prefix}/lib/rpm/get_magic.pl
%rpmattr	%{__prefix}/lib/rpm/getpo.sh
%rpmattr	%{__prefix}/lib/rpm/http.req
%rpmattr	%{__prefix}/lib/rpm/javadeps
%rpmattr	%{__prefix}/lib/rpm/magic
%rpmattr	%{__prefix}/lib/rpm/magic.mgc
%rpmattr	%{__prefix}/lib/rpm/magic.mime
%rpmattr	%{__prefix}/lib/rpm/magic.mime.mgc
%rpmattr	%{__prefix}/lib/rpm/magic.prov
%rpmattr	%{__prefix}/lib/rpm/magic.req
%rpmattr	%{__prefix}/lib/rpm/perldeps.pl
%rpmattr	%{__prefix}/lib/rpm/perl.prov
%rpmattr	%{__prefix}/lib/rpm/perl.req

%rpmattr	%{__prefix}/lib/rpm/rpm[bt]
%rpmattr	%{__prefix}/lib/rpm/rpmdeps
%rpmattr	%{__prefix}/lib/rpm/trpm
%rpmattr	%{__prefix}/lib/rpm/u_pkg.sh
%rpmattr	%{__prefix}/lib/rpm/vpkg-provides.sh
%rpmattr	%{__prefix}/lib/rpm/vpkg-provides2.sh

%{__mandir}/man8/rpmbuild.8*
%{__mandir}/man8/rpmdeps.8*

%if %{with_python_subpackage}
%files python
%defattr(-,root,root)
%{__libdir}/python%{with_python_version}/site-packages/rpmmodule.so
%{__libdir}/python%{with_python_version}/site-packages/rpmdb
%endif

%files devel
%defattr(-,root,root)
%if %{with_apidocs}
%doc apidocs
%endif
%{__includedir}/rpm
%{__libdir}/librpm.a
%{__libdir}/librpm.la
%{__libdir}/librpm.so
%{__libdir}/librpmdb.a
%{__libdir}/librpmdb.la
%{__libdir}/librpmdb.so
%{__libdir}/librpmio.a
%{__libdir}/librpmio.la
%{__libdir}/librpmio.so
%{__libdir}/librpmbuild.a
%{__libdir}/librpmbuild.la
%{__libdir}/librpmbuild.so
%{__mandir}/man8/rpmcache.8*
%{__mandir}/man8/rpmgraph.8*
%rpmattr	%{__prefix}/lib/rpm/rpmcache
%rpmattr	%{__bindir}/rpmgraph

%files -n popt
%defattr(-,root,root)
%{__libdir}/libpopt.so.*
%{__mandir}/man3/popt.3*
%lang(cs)	%{__prefix}/*/locale/cs/LC_MESSAGES/popt.mo
%lang(da)	%{__prefix}/*/locale/da/LC_MESSAGES/popt.mo
%lang(de)	%{__prefix}/*/locale/de/LC_MESSAGES/popt.mo
%lang(es)	%{__prefix}/*/locale/es/LC_MESSAGES/popt.mo
%lang(eu_ES)	%{__prefix}/*/locale/eu_ES/LC_MESSAGES/popt.mo
%lang(fi)	%{__prefix}/*/locale/fi/LC_MESSAGES/popt.mo
%lang(fr)	%{__prefix}/*/locale/fr/LC_MESSAGES/popt.mo
%lang(gl)	%{__prefix}/*/locale/gl/LC_MESSAGES/popt.mo
%lang(hu)	%{__prefix}/*/locale/hu/LC_MESSAGES/popt.mo
%lang(id)	%{__prefix}/*/locale/id/LC_MESSAGES/popt.mo
%lang(is)	%{__prefix}/*/locale/is/LC_MESSAGES/popt.mo
%lang(it)	%{__prefix}/*/locale/it/LC_MESSAGES/popt.mo
%lang(ja)	%{__prefix}/*/locale/ja/LC_MESSAGES/popt.mo
%lang(ko)	%{__prefix}/*/locale/ko/LC_MESSAGES/popt.mo
%lang(no)	%{__prefix}/*/locale/no/LC_MESSAGES/popt.mo
%lang(pl)	%{__prefix}/*/locale/pl/LC_MESSAGES/popt.mo
%lang(pt)	%{__prefix}/*/locale/pt/LC_MESSAGES/popt.mo
%lang(pt_BR)	%{__prefix}/*/locale/pt_BR/LC_MESSAGES/popt.mo
%lang(ro)	%{__prefix}/*/locale/ro/LC_MESSAGES/popt.mo
%lang(ru)	%{__prefix}/*/locale/ru/LC_MESSAGES/popt.mo
%lang(sk)	%{__prefix}/*/locale/sk/LC_MESSAGES/popt.mo
%lang(sl)	%{__prefix}/*/locale/sl/LC_MESSAGES/popt.mo
%lang(sr)	%{__prefix}/*/locale/sr/LC_MESSAGES/popt.mo
%lang(sv)	%{__prefix}/*/locale/sv/LC_MESSAGES/popt.mo
%lang(tr)	%{__prefix}/*/locale/tr/LC_MESSAGES/popt.mo
%lang(uk)	%{__prefix}/*/locale/uk/LC_MESSAGES/popt.mo
%lang(wa)	%{__prefix}/*/locale/wa/LC_MESSAGES/popt.mo
%lang(zh)	%{__prefix}/*/locale/zh/LC_MESSAGES/popt.mo
%lang(zh_CN)	%{__prefix}/*/locale/zh_CN.GB2312/LC_MESSAGES/popt.mo

# XXX These may end up in popt-devel but it hardly seems worth the effort.
%{__libdir}/libpopt.a
%{__libdir}/libpopt.la
%{__libdir}/libpopt.so
%{__includedir}/popt.h

%changelog
* Fri Sep 17 2004 Jeff Johnson <jbj@redhat.com> 4.3.2-5
- remove rpm <-> rpm-libs dependency loop.
- print dependency whiteout iff --anaconda is specified.

* Wed Sep 15 2004 Jeff Johnson <jbj@redhat.com> 4.3.2-4
- print dependency loops as warning iff --anaconda is specified.

* Sat Sep  4 2004 Jeff Johnson <jbj@redhat.com> 4.3.2-2
- ia64: make sure that autorelocated file dependencies are satisfied.
- ia64: relocate all scriptlet interpreters.
- ia64: don't bother trying to preload autorelocated modules.
- fix: filesystem package needs mail/lock w/o getgrnam.
- fix: do getpwnam/getgrnam to load correct modules before chroot.
- restore file conflict detection traditional behavior.

* Fri Aug 20 2004 Jeff Johnson <jbj@redhat.com> 4.3.2-0.9
- fix: static glibc/libgcc helpers always installed (#127522).
- fix: defattr for rpm-libs (#130461).

* Thu Aug 19 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.7
- shared libraries in separate rpm-libs package.
- avoid "can't happen" recursion while retrieving pubkeys.
- add ppc32dy4 arch.
- make peace with automake 1.9.1.

* Fri Jul  9 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.6
- fix: evaluate rather than default file_contexts path. (#127501).

* Mon Jul  5 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.5
- change default behavior to resolve file conflicts as LIFO.
- add --fileconflicts to recover rpm traditional behavior.
- prefer elf64 over elf32 files, everywhere and always (#126853).
- ia64: auto-relocate entire, not partial, directory contents (#126905).
- ia64: auto-relocate glibc.ix86 interpreter path (#100563).

* Wed Jun 16 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.4
- add ppc8[25]60 arches.

* Mon Jun 14 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.3
- add 'requires' and 'conflicts' tag aliases.
- python: return ds, not tuple, for ds iteration.
- python: permit integer keys to ts.dbMatch().
- xml: use <foo/> markup for empty tags.
- xml: <integer/> instead of <integer>0</integer> markup.
- fix: disable fingerprint generation on kernel paths.

* Tue Jun  8 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.2
- lua embedded in rpmio.
- use lua to identify desired selinux file context regexes.

* Tue Jun  1 2004 Jeff Johnson <jbj@jbj.org> 4.3.2-0.1
- use /etc/selinux/targeted/contexts/files/file_contexts for now.
- disable file contexts into package metadata during build.
- fix: dev package build on s390x hack around.
- fix: "/path/foo.../bar" was losing a dot (#123844).
- fix: PIE executables have basename-as-soname provides (#123697).
- add aurora/sparc patches (#124469).
- use poll(2) if available, avoid borked aurora/sparc select (#124574).
