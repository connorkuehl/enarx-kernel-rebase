# enarx-kernel-rebase

A script for rebasing custom Fedora kernels. It will take the following
actions:

For each branch defined in the manifest (see below):

1. Copy your local branch to a new (temporary) branch
1. Fetch changes from the target upstream branch
1. Perform a rebase against the target upstream branch
1. Produce a source RPM (SRPM)
1. Upload the SRPM into the specified COPR repository
1. Reset (save) the local branch to the successfully rebased temporary branch
1. Remove the temporary branch
1. Remove the SRPM that was safely uploaded to COPR

If the script encounters an error at any step, it will complain,
create a tombstone blocker file for the branch, and write the
name of the temporary branch to the blocker file. It will not
delete the temporary branch if it is used to create a blocker file.

Look for a file in the repository root with a name like
`blocked.localbranch` where `localbranch` = the name of
your local branch defined in the manifest.

If the script detects a blocker file for a branch, the branch will
be skipped. It will still complain before moving on just in case
one forgets to remove the blocker file once the issue has been
resolved.

## Prerequisites

The following programs must be installed and in your PATH:

1. `copr-cli`
1. `git`
1. `fedpkg`

The following Python dependencies must be installed:

1. `toml`

These have been committed to `requirements.txt`, so for convenience:

```console
$ python3 -m pip install --user -r requirements.txt
```

You must have a Fedora kernel git tree cloned somewhere accessible
to you. If you plan to do any other actions against the package,
such as building it or running `fedpkg prep`, you will need to
also install the build dependencies for the kernel package. 
[How?](https://fedoraproject.org/wiki/Building_a_custom_kernel#Building_a_Kernel_from_the_Fedora_source_tree)

You must have your COPR token saved somewhere `copr-cli` can find it.
[How?](https://developer.fedoraproject.org/deployment/copr/copr-cli.html)

You must create a manifest (in TOML). For example:

```toml
copr = 'npmccallum/enarx'
remote = 'https://src.fedoraproject.org/rpms/kernel.git'

[[branch]]
release = 'f32'
remote = 'f32'
local = 'f32-enarx'
chroot = 'fedora-32-x86_64'

[[branch]]
release = 'f33'
remote = 'f33'
local = 'f33-enarx'
chroot = 'fedora-33-x86_64'

[[branch]]
release = 'master'
remote = 'master'
local = 'f34-enarx'
chroot = 'fedora-rawhide-x86_64'
```

The manifest describes:

* `copr`: Which COPR repo should the packages be uploaded to?
* `remote`: What is the upstream git remote for the package you're rebasing against?
* `branch`: Each branch you'd like to rebase against and create packages for.
  * `remote`: Which upstream remote branch to rebase onto.
  * `release`: Which Fedora release this package is targeting.
  * `local`: The name of your local git branch you'd like rebased on top of the `remote` branch.
  * `chroot`: The COPR chroot to use for the build.

## Usage

```console
$ ./enarx-kernel-rebase.py --help
usage: enarx-kernel-rebase.py [-h] [-d] [-c CWD] [-m MANIFEST]

Rebase the Enarx kernels

optional arguments:
  -h, --help            show this help message and exit
  -d, --dryrun
  -c CWD, --cwd CWD
  -m MANIFEST, --manifest MANIFEST
```

Example:

```console
$ ./enarx-kernel-rebase.py --dryrun --cwd ~/pkg/kernel --manifest ~/pkg/enarx.toml
```

If you do not invoke the script from the folder that your repository is in,
you'll need to use the `--cwd` argument so the script can change directory to
the repo.

It's important that the script runs from the repository root because it runs
git commands as if it was in the repository root.

## Updating/Adding a patch set

The most relevant example here will be the usecase that motivates this entire
repository: applying the Intel SGX patches to the Fedora kernel.

1. If necessary, enable relevant config options in the relevant files.
1. Go to the [linux-sgx](https://patchwork.kernel.org/project/intel-sgx/list/)
patchwork and download the latest patch set.
    1. To do this, simply click on one of the patches that belongs to the (latest)
    revision of the SGX patches. These are easily spotted as they start with
    something like "[v38,n/m] blah blah blah"
    1. Click on the "series" button to the right. This will download the entire patch set as a single patch file.
    1. Save this file to the packaging repo as something like `1000-sgx-38.patch`.
1. Remove the old patch set if it is committed to the repository.
1. Add/edit a `Patch1000: 1000-sgx-38.patch` entry in the `kernel.spec`
1. Modify the `buildid` to reflect the change.
1. Sanity check that the patches apply:

```console
$ fedpkg --release $RELEASE prep
```

Example commits:

Enabling a config option:

```diff
commit 60cc6d95d69f1e09842d37d6d0f31e7abde5e865
Author: Connor Kuehl <ckuehl@redhat.com>
Date:   Tue Sep 22 14:33:46 2020 -0500

    CONFIG_INTEL_SGX=y

diff --git a/kernel-x86_64-debug-fedora.config b/kernel-x86_64-debug-fedora.config
index cebeeb4c25f6..10d82442f4c1 100644
--- a/kernel-x86_64-debug-fedora.config
+++ b/kernel-x86_64-debug-fedora.config
@@ -2594,6 +2594,7 @@ CONFIG_INTEL_RST=m
 CONFIG_INTEL_SCU_IPC_UTIL=m
 CONFIG_INTEL_SCU_PCI=y
 CONFIG_INTEL_SCU_PLATFORM=m
+CONFIG_INTEL_SGX=y
 CONFIG_INTEL_SMARTCONNECT=y
 CONFIG_INTEL_SOC_DTS_THERMAL=m
 CONFIG_INTEL_SOC_PMIC_BXTWC=m
diff --git a/kernel-x86_64-fedora.config b/kernel-x86_64-fedora.config
index 0c78b7a63601..3ca1f0d75da6 100644
--- a/kernel-x86_64-fedora.config
+++ b/kernel-x86_64-fedora.config
@@ -2577,6 +2577,7 @@ CONFIG_INTEL_RST=m
 CONFIG_INTEL_SCU_IPC_UTIL=m
 CONFIG_INTEL_SCU_PCI=y
 CONFIG_INTEL_SCU_PLATFORM=m
+CONFIG_INTEL_SGX=y
 CONFIG_INTEL_SMARTCONNECT=y
 CONFIG_INTEL_SOC_DTS_THERMAL=m
 CONFIG_INTEL_SOC_PMIC_BXTWC=m

```

```diff
diff --git a/kernel.spec b/kernel.spec
index 1e0e48b89fb1..e1df0d04171f 100644
--- a/kernel.spec
+++ b/kernel.spec
@@ -59,7 +59,7 @@ Summary: The Linux kernel
 %global zipsed -e 's/\.ko$/\.ko.xz/'
 %endif
 
-# define buildid .local
+%define buildid .1.enarx.sgx.38
 
 
 %if 0%{?fedora}
@@ -790,6 +790,8 @@ Patch73: 0001-Work-around-for-gcc-bug-https-gcc.gnu.org-bugzilla-s.patch
 Patch74: 0001-Temporarily-remove-cdomain-from-sphinx-documentation.patch
 Patch75: 0001-Filter-out-LTO-build-options-from-the-perl-ccopts.patch
 
+Patch1000: 1000-sgx-38.patch
+
 %endif
 
 # empty final patch to facilitate testing of kernel patches
```

## When things go wrong

### Failed to rebase

This whole thing works by rebasing a small set of changes in the `kernel.spec`
file against the upstream Fedora `kernel.spec`. The upstream file occasionally
adds additional patches which may result in a merge conflict. These are often
very easy to fix. When resolving the merge conflict in the `kernel.spec`, just
accept all the changes from upstream and put the patches we're including right
beneath them.

### Fedora did a huge rebase

The Fedora kernels are refreshingly new. Sometimes the `kernel.spec` changes
so drastically it's not worth the time fixing the merge conflicts. **WARNING: the
next sentence instruction is a destructive action, so go ahead and back up any
changes you care to keep.** Go ahead and hard reset the branch to the upstream
Fedora branch.

We can recreate the Enarx kernel easily enough by hand. This is described in
the "Updating/Adding a patch set" section above.

### Uploaded package fails to build

This is most likely because the patch set we're going through the trouble to rebase
with failed to apply. As mentioned before, the Fedora kernels move quickly and so
does the patch set we're trying to track.

This could be for a number of reasons. Here are the most common:

* The patch set no longer applies. You can sanity check for this with
`fedpkg --release $RELEASE prep`.
* The kernel is too new and the patchset is too old. Check to see if there's a new
version of the patchset that applies to this kernel.
* The patchset is too new and the kernel is too old. Either apply an older revision
of the patchset or get a newer kernel that it does apply to.
* You did a backport and made a mistake (or an update to the kernel made your
backport incorrect).

Obviously for some of these you're kind of waiting for a new patch set or you're
waiting for the Fedora kernel to catch up to a point where the newer patch set
applies cleanly.

### Timed out copr-cli build command

This happens sometimes. The script already rate limits itself. Sometimes you just
have to try again later.