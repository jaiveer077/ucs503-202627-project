![TIET Logo](assets/tiet-logo.svg){ .tiet-logo }

**UCS503: Software Engineering (Project)**
**TIET Patiala**

# The Sum Function in C++

**Author(s):**

* `Jaiveer Singh` `<jsingh_be24@thapar.edu>`
* `Harshjyot Kaur` `<hkaur4_be24@thapar.edu>`
* `Avneet Kaur` `<akaur5_be24@thapar.edu>`
* `Archita Sharma` `<asharma20_be24@thapar.edu>`

This project creates a sum function in C++ as a sample to illustrate how to compile a shared library and distribute it for use along with the binary.

## Installation

```shell
make -C code
```

This will create a folder `dist` in the `code` folder, with the following contents:

```text
dist
 +-lib
 |  \-libbvr_math.so
 +-bin
    \-run
```

## Usage

```shell
cd code
export LD_LIBRARY_PATH=dist/lib
./dist/bin/run
```
