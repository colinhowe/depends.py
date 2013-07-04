import argparse
import ast
import itertools
import os
import sys
import re

def _passes_filters(path, excludes):
    for exclude in excludes:
        if re.match(exclude, path):
            return False
    return True

def _get_all_files(root_path, excludes):
    if root_path.endswith('/'):
        root_path = root_path[:-1]

    for root, dirs, files in os.walk(root_path):
        for f in files:
            path = '%s/%s' % (root, f)
            if not f.endswith('.py'):
                continue
            if _passes_filters(path, excludes):
                yield os.path.relpath(path)

def _get_all_modules(package_paths, excludes):
    module_paths = []
    for package_path in package_paths:
        module_paths += _get_all_files(package_path, excludes)
    return module_paths

def _get_imports_from_ast(node):
    if isinstance(node, list):
        return itertools.chain(*[_get_imports_from_ast(child) for child in node])
    elif isinstance(node, ast.ImportFrom):
        return [node.module]
    elif isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    else:
        return []

def _get_dependencies(module):
    with open(module, 'r') as in_file:
        contents = in_file.read()
    tree = ast.parse(contents)
    return list(_get_imports_from_ast(tree.body))

def _resolve_dependency(module, dependency, all_modules):
    module_path = '/'.join(module.split('/')[:-1])

    # Convert the dependency into something more pathlike
    dependency = dependency.replace('.', '/')

    # Check the immediate path first
    immediate_module = "%s/%s.py" % (module_path, dependency)
    if immediate_module in all_modules:
        return dependency
    immediate_package = "%s/%s/__init__.py" % (module_path, dependency)
    if immediate_package in all_modules:
        return dependency

    # Check the root path
    root_module = "%s.py" % dependency
    if root_module in all_modules:
        return dependency
    root_package = "%s/__init__.py" % dependency
    if root_package in all_modules:
        return dependency

emitted_modules = set()

def _emit_module(module):
    if module not in emitted_modules:
        emitted_modules.add(module)
        print '"%s" [style=filled];' % module

def _resolve_dependencies(module, all_modules):
    clean_module = module[:-3]
    _emit_module(clean_module)
    dependencies = _get_dependencies(module)
    for dependency in dependencies:
        dependency = _resolve_dependency(module, dependency, all_modules)
        if dependency:
            _emit_module(dependency)
            print '"%s" -> "%s";' % (clean_module, dependency)

parser = argparse.ArgumentParser(description='Create a dependency graph of the given folder')

parser.add_argument('package_paths', nargs='+',
                   help='the packages to process')
parser.add_argument('--exclude', nargs='+',
                   help='regular expressions of paths to ignore')

args = parser.parse_args()
package_paths = args.package_paths
excludes = args.exclude or []

all_modules = _get_all_modules(['.'], [])
relevant_modules = _get_all_modules(package_paths, excludes)

print """
# This file was generated by depends.py

strict digraph "dependencies" {
    graph [
        rankdir = "LR",
        overlap = "scale",
        size = "8,10",
        ratio = "fill",
        fontsize = "16",
        fontname = "Helvetica",
        clusterrank = "local"
    ]

    node [
        fontsize=7
        shape=ellipse
    ];
"""
for module in relevant_modules:
    _resolve_dependencies(module, all_modules)


print "}"
