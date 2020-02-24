#!/bin/bash
set -e

src_version=$(python3 setup.py --version)
package_version=1
software_name=$(python3 setup.py --name)

BUILD_DIRECTORIES="dist ${software_name}.egg-info"

function clean_build_directories {
    echo "--- Cleaning Build Directories ---"
    for directory in ${BUILD_DIRECTORIES}; do
        if [ -d ${directory} ]; then
            rm -rf ${directory}
        fi
    done
}

function build_python_package {
    echo "--- Building Python Package ---"
    echo -e "[install]\nprefix=/" > setup.cfg
    python3 setup.py sdist --formats=gztar
}

function build_debian_package {
    echo "--- Building Debian Package ---"
    mv dist/${software_name}-${src_version}.tar.gz dist/${software_name}_${src_version}.orig.tar.gz
    tar -C dist -xvf dist/${software_name}_${src_version}.orig.tar.gz
    mv dist/${software_name}-${src_version} dist/${software_name}_${src_version}
    cp -r debian dist/${software_name}_${src_version}/debian
    (cd dist/${software_name}_${src_version}/ && dpkg-buildpackage -us -uc)
    mv dist/${software_name}_${src_version}-${package_version}_all.deb packages/
    cp dist/${software_name}_${src_version}.orig.tar.gz packages/
}

clean_build_directories
build_python_package
build_debian_package
clean_build_directories