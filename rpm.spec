%define	with_python_subpackage	1%{nil}
%define	with_python_version	2.2%{nil}
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
%define version 4.2
Version: %{version}
%{expand: %%define rpm_version %{version}}
Release: 1
Group: System Environment/Base
Source: ftp://ftp.rpm.org/pub/rpm/dist/rpm-4.0.x/rpm-%{rpm_version}.tar.gz
Copyright: GPL
Conflicts: patch < 2.5
%ifos linux
Prereq: fileutils shadow-utils
%endif
Requires: popt = 1.8
Obsoletes: rpm-perl < %{version}

# XXX necessary only to drag in /usr/lib/libelf.a, otherwise internal elfutils.
BuildRequires: elfutils-libelf

BuildRequires: zlib-devel

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

%package devel
Summary:  Development files for manipulating RPM packages.
Group: Development/Libraries
Requires: rpm = %{rpm_version}

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
Requires: rpm = %{rpm_version}, patch >= 2.5, file
Provides: rpmbuild(VendorConfig) = 4.1-1

%description build
The rpm-build package contains the scripts and executable programs
that are used to build packages using the RPM Package Manager.

%if %{with_python_subpackage}
%package python
Summary: Python bindings for apps which will manipulate RPM packages.
Group: Development/Libraries
Requires: rpm = %{rpm_version}
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
Version: 1.8

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
%ifarch x86_64 s390 s390x 
CFLAGS="$RPM_OPT_FLAGS -fPIC"; export CFLAGS
%else
CFLAGS="$RPM_OPT_FLAGS"; export CFLAGS
%endif
CFLAGS="$RPM_OPT_FLAGS" ./configure --prefix=%{__prefix} --sysconfdir=/etc \
	--localstatedir=/var --infodir='${prefix}%{__share}/info' \
	--mandir='${prefix}%{__share}/man' \
	$WITH_PYTHON --without-javaglue
%else
CFLAGS="$RPM_OPT_FLAGS" ./configure --prefix=%{__prefix} $WITH_PYTHON \
	--without-javaglue
%endif

# XXX hack out O_DIRECT support in db4 for now.
perl -pi -e 's/#define HAVE_O_DIRECT 1/#undef HAVE_O_DIRECT/' db3/db_config.h

make

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
#    exit 1
fi
/usr/sbin/groupadd -g 37 rpm				> /dev/null 2>&1
/usr/sbin/useradd  -r -d /var/lib/rpm -u 37 -g 37 rpm	> /dev/null 2>&1
%endif
exit 0

%post
%ifos linux
/sbin/ldconfig
/bin/chown rpm.rpm /var/lib/rpm/[A-Z]*
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

%{__libdir}/librpm-4.2.so
%{__libdir}/librpmdb-4.2.so
%{__libdir}/librpmio-4.2.so
%{__libdir}/librpmbuild-4.2.so

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
%ifarch sparc sparcv9 sparc64
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
%rpmattr	%{__prefix}/lib/rpm/rpmdb_deadlock
%rpmattr	%{__prefix}/lib/rpm/rpmdb_dump
%rpmattr	%{__prefix}/lib/rpm/rpmdb_load
%rpmattr	%{__prefix}/lib/rpm/rpmdb_loadcvt
%rpmattr	%{__prefix}/lib/rpm/rpmdb_svc
%rpmattr	%{__prefix}/lib/rpm/rpmdb_stat
%rpmattr	%{__prefix}/lib/rpm/rpmdb_verify
%rpmattr	%{__prefix}/lib/rpm/rpmfile
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
* Wed Mar 19 2003 Jeff Johnson <jbj@redhat.com> 4.2-1
- release candidate.
- hack out O_DIRECT support in db4 for now.

* Fri Mar 14 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.73
- fix: short option help missing string terminator.

* Fri Mar 14 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.72
- fix: close db cursors to remove rpmdb references on signal exit.

* Fri Mar  7 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.70
- fix: memory leak (85522).
- build with internal elfutils if not installed.

* Thu Feb 27 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.69
- file: check size read from elf header (#85297).

* Thu Feb  6 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.66
- popt: diddle doxygen/splint annotations, corrected doco.
- file: fix ogg/vorbis file classification problems.
- skip fingerprints in /usr/share/doc and /usr/src/debug.
- add file(1) as /usr/lib/rpm/rpmfile.
- enable transaction coloring for s390x/ppc64.

* Fri Jan 31 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.65
- fix: trap SIGPIPE, close database(s).
- configurable default query output format.

* Wed Jan 29 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.64
- pay attention to package color when upgrading identical packages.

* Tue Jan 28 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.63
- fix: clean relocation path for --prefix=/.
- python: permit stdout/stderr to be remapped to install.log.

* Mon Jan 27 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.62
- fix: more debugedit.c problems.

* Sat Jan 25 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.61
- permit anaconda to choose "presentation order".

* Wed Jan 22 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.60
- fix: debugedit.c problem.

* Fri Jan 17 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.58
- duplicate package checks with arch/os checks if colored.
- file conflict checks with colors.

* Mon Jan 13 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.57
- teach rpmquery to return "owning" package(s) in spite of alternatives.

* Sun Jan 12 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.56
- file: *really* read elf64 notes correctly.
- python: restore thread context on errorCB (#80744).

* Fri Jan 10 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.55
- fix: obscure corner case(s) with rpmvercmp (#50977).

* Wed Jan  8 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.54
- python: put rpmmodule.so where python expects to find.
- add brp-strip-static-archive build root policy helper.
- add -lelf to rpm LDFLAGS, not LDADD, since there is no libelf.la now.

* Tue Jan  7 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.53
- file: read elf64 notes correctly.

* Mon Jan  6 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.52
- portabilitly: solaris fixes.
- for DSO's, provide the file basename if DT_SONAME not found.
- add perldeps.pl, start to replace perl.{prov,req}.

* Sun Jan  5 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.51
- file: avoid ogg/vorbis file classification problems.

* Wed Jan  1 2003 Jeff Johnson <jbj@redhat.com> 4.2-0.49
- add rpmts/rpmte/rpmfi/rpmds element colors.
- ignore items not in our rainbow (i.e. colors are functional).
- fix: dependency helpers now rate limited at 10ms, not 1s.
- add per-arch canonical color, only x86_64 enabled for now.

* Sun Dec 29 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.46
- don't segfault with packages produced by rpm-2.93 (#80618).
- python: eliminate hash.[ch] and upgrade.[ch], methods too.
- fix :armor query extension, tgpg mktmp handling (#80684).
- use rpmfiFClass() underneath --fileclass.
- use rpmfiFDepends() underneath --fileprovide and --filerequire.
- python: add fi.FColor() and fi.FClass() methods.
- calculate dependency color and refernces.
- python: add ds.Color() and ds.Refs() methods.
- fix: typo in assertion.

* Sat Dec 28 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.45
- error if querying with iterator on different sized arrays.
- add rpmfi methods to access color, class, and dependencies.

* Fri Dec 27 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.42
- add BETA-GPG-KEY (but not in headers using %%pubkey yet).
- disable perl module magic rule.
- ignore ENOENT return from db->close (#80514,#79314).
- fix builddir relative inclusion, add %%pubkeys to rpm header.
- fix: package relocations were broken (#75057).

* Thu Dec 26 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.39
- add Red Hat pubkeys to rpm header.
- resurrect automagic perl(foo) dependency generation.

* Tue Dec 24 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.38
- add %%pubkey attribute to read armored pubkey files into header.
- permit both relative/absolute paths, display 'P' when verifying.

* Mon Dec 23 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.36
- add matching "config(N) = EVR"  dependencies iff %%config is found.

* Sun Dec 22 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.35
- fix: remove rpmfi scareMem so that headers can be reloaded on ia64.
- fix: set DB_PRIVATE, not DB_ENV_PRIVATE, if unshared posix mutexes.
- remove useless (and now unnecessary) kernel/glibc dependencies (#79872).

* Sat Dec 21 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.34
- add --enable-posixmutexes when configuring on linux.
- add rpmdb_{deadlock,dump,load,svc,stat,verify} utilities.
- include srpm pkgid in binary headers (#71460).
- add %%check scriptlet to run after %%install (#64137).
- simplify specfile query linkage loop.
- drill rpmts into parseSpec(), carrying Spec along.

* Fri Dec 20 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.33
- dynamically link /bin/rpm, link against good old -lpthread.
- test pthread_{mutex,cond}attr_setpshared(), add DB_ENV_PRIVATE if not.
- error on exclusive Packages fcntl lock if DB_ENV_PRIVATE is set.
- copy compressFilelist to convertdb1.c, remove internal legacy.h.

* Thu Dec 19 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.31
- statically link against /usr/lib/nptl/libpthread.a, if present.
- remove popt aliases for -U et al.
- add -I/usr/include/nptl, Conflicts: kernel < 2.4.20.

* Wed Dec 18 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.29nptl
- popt aliases for -U et al to achieve dynamic link with nptl.
- add --file{class,provide,require} popt aliases and header extensions.

* Tue Dec 17 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.28nptl
- re-enable CDB locking, removing "private" from %%__dbi_cdb macro.

* Mon Dec 16 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.27+nptl
- rebuild against glibc with fcntl fixed in libpthread.

* Sun Dec 15 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.26+nptl
- disable fcntl(2) lock on Packages until glibc+nptl is fixed.
- make cdb locks "private" for pthreads compatibility w/o NPTL.
- add --enable-posixmutexes to use NPTL.
- make dependency generation "opt-out" everywhere.

* Sat Dec 14 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.25
- rebuild rpm with internal dependency generation enabled.
- fix: make sure each library has DT_NEEDED for all unresolved syms.
- generate Elf provides even if file is not executable.

* Fri Dec 13 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.24
- debug_packages "works", but non-noarch w/o %setup has empty payload.
- make dependency generation "opt-in" in order to build in distro.

* Thu Dec 12 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.23
- fix: add rpmlib(VersionedDependencies) if versioned Provides: found.
- fix: add %%ifnarch noarch to debug_package macro.

* Wed Dec 11 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.22
- rebuild against glibc with TLS support.

* Tue Dec 10 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.21
- don't generate dependencies unless execute bit is set.
- enable internal automagic dependency generation as default.

* Sat Dec  7 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.19
- resurrect  AutoReq: and AutoProv:.

* Tue Dec  2 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.18
- internal automagic dependency generation (disabled for now).

* Mon Dec  1 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.17
- late rpmts reference causes premature free (#78862).

* Sun Dec  1 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.16
- link rpm libraries together, use shared helpers with external -lelf.
- move libfmagic to librpmio.
- use libtool-1.4.3, autoconf-2.56.
- add explicit -L/lib64 -L/usr/lib64 for libtool mode=relink on x86_64.
- use usrlib_LTLIBRARIES to install directly in /usr/lib64 instead.

* Sat Nov 30 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.14
- upgrade to elfutils-0.63.

* Fri Nov 29 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.13
- bundle libfmagic into librpmbuild for now.
- apply patches 7 and 8 to db-4.1.24.
- upgrade to elfutils-0.59.
- add -g to all platforms optflags.
- build with external elfutils (preferred), if available.

* Wed Nov 20 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.12
- use rpmdeps rather than find-{requires,provides}.

* Tue Nov 19 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.11
- fix: option conflict error message (#77373).
- add AC_SYS_LARGFILE throughout.
- statically link rpmdeps against (internal) libfmagic.

* Fri Nov 15 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.10
- update to elfutils-0.56.
- have debug sub-subpackage use external, not internal, elfutils.
- apply patches 1-6 to db-4.1.24.
- resurrect availablePackages one more time.

* Wed Nov 13 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.8
- fix: bash must have functional libtermcap.so.2.

* Sat Nov  9 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.7
- add _javadir/_javadocdir/_javaclasspath macros.

* Fri Nov  8 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.6
- fix: /dev/initctl has not MD5 segfault (#76718).
- rpm.8: gpg uses GNUPGHOME, not GPGPATH (#76691).
- use %%{_lib} for libraries.
- fix: permit build with --disable-nls (#76258).
- add error message on glob failure (#76012).
- remove dependency on libelf.

* Thu Oct 24 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.5
- add /usr/lib/rpm/rpmdeps.
- add /usr/lib/rpm/magic.

* Wed Oct 23 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.4
- resurrect genhdlist "greased lightning" pathway for now.
- elfutils: avoid gcc-3.2 ICE on x86_64 for now.

* Fri Oct 18 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.2
- add debug sub-package patch.
- re-add elfutils/libdwarf (for dwarf.h), eliminate tools/dwarf2.h.

* Thu Oct 17 2002 Jeff Johnson <jbj@redhat.com> 4.2-0.1
- set cachesize without a dbenv, the default is far too small.
- db: don't return EACCES on db->close w/o environment.
- unify cachesize configuration, with (or without) a dbenv.
- comments regarding unsupported (yet) db-4.1.17 functionality.
- requirement on libelf >= 0.8.2 to work around incompatible soname (#72792).
- fix: common sanity check on headers, prevent segfault (#72590).
- limit number of NOKEY/UNTRUSTED keys that will be warned once.
- libadd -lelf to rpmdb (#73024).
- update to db-4.1.24 final.
- eliminate myftw, use Fts(3) instead.
- dump libelf, gulp elfutils, for now.
- python: permit headers to be hashed.
- use %%{_lib} for libraries.
