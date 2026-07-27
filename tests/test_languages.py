"""Coverage of build_digest for every language in specs.SPECS (plus markdown,
which has no spec entry but is handled specially). Each case pairs a small
source snippet with a set of substrings the digest must contain - line
numbers included, so a regression in _walk/_extract_sig/header building
shows up immediately."""
import pytest

from structural_digest import build_digest

JAVA_SRC = b"""package com.example;

import java.util.List;
import com.example.util.Helper;

public class Foo {
    private int x, y;
    public Foo() {
    }
    public void bar() {
    }
}
"""

KOTLIN_SRC = b"""package com.example

import java.util.List

class Foo {
    private val x: Int = 0
    fun bar() {
    }
}
"""

PYTHON_SRC = b"""import os
from typing import List


class Foo:
    def __init__(self):
        pass

    def _helper(self):
        pass

    def bar(self):
        pass
"""

TYPESCRIPT_SRC = b"""import { List } from './list';
import fs from 'fs';

export interface Greeter {
  greet(): string;
}

export class Foo {
  private x: number = 0;
  #secret: number = 0;
  bar(): void {
  }
}

export const make = (): Foo => {
  return new Foo();
};
"""

TSX_SRC = b"""import React from 'react';

export function Card(props: { title: string }) {
  return <div className="card">{props.title}</div>;
}
"""

JAVASCRIPT_SRC = b"""import fs from 'fs';
import { helper } from './helper';

export class Foo {
  #secret = 0;
  bar() {
  }
}

export function baz() {
}

export const make = () => {
  return new Foo();
};
"""

CSHARP_SRC = b"""using System;
using MyApp.Utils;

namespace MyApp
{
    public class Foo
    {
        private int x, y;
        public Foo()
        {
        }
        public void Bar()
        {
        }
    }
}
"""

RUST_SRC = b"""use std::fmt;
use serde::Serialize;

pub struct Foo {
    pub x: i32,
    y: i32,
}

impl Foo {
    pub fn new() -> Foo {
        Foo { x: 0, y: 0 }
    }

    fn helper(&self) -> i32 {
        self.y
    }
}
"""

GO_SRC = b"""package main

import (
\t"fmt"
\t"github.com/foo/bar"
)

type Foo struct {
\tX int
\ty int
}

type Greeter interface {
\tHello() string
}

func (f *Foo) Bar() string {
\treturn fmt.Sprint(f.X)
}

func helper() int {
\treturn 0
}
"""

GROOVY_SRC = b"""plugins {
    id 'java'
}

dependencies {
    implementation 'com.example:lib:1.0'
}
"""

MARKDOWN_SRC = b"""# Title

Some text.

## Section

More text.
"""

LANGUAGE_CASES = [
    ("java", JAVA_SRC, [
        "package com.example; imports: util.Helper",
        "L6: public class Foo",
        "L7: field: private int x, y",
        "L8: public Foo()",
        "L10: public void bar()",
    ]),
    ("kotlin", KOTLIN_SRC, [
        "package com.example; imports: util.List",
        "L5: class Foo",
        "L6: field: private val x: Int = 0",
        "L7: fun bar()",
    ]),
    ("python", PYTHON_SRC, [
        "imports: none notable (2 stdlib/common)",
        "L5: class Foo",
        "L6: def __init__(self)",
        "L9: def _helper(self)",
        "L12: def bar(self)",
    ]),
    ("typescript", TYPESCRIPT_SRC, [
        "imports: ./list",
        "L4: interface Greeter",
        "L5: greet(): string",
        "L8: class Foo",
        "L9: field: private x: number = 0",
        "L10: field: #secret: number = 0",
        "L11: bar(): void",
        "L15: const make = (): Foo =>",
    ]),
    ("tsx", TSX_SRC, [
        "imports: react",
        "L3: function Card(props: { title: string })",
    ]),
    ("javascript", JAVASCRIPT_SRC, [
        "imports: ./helper",
        "L4: class Foo",
        "L5: field: #secret = 0",
        "L6: bar()",
        "L10: function baz()",
        "L13: const make = () =>",
    ]),
    ("csharp", CSHARP_SRC, [
        "namespace MyApp; imports: MyApp.Utils",
        "L4: namespace MyApp",
        "L6: public class Foo",
        "L8: field: private int x, y",
        "L9: public Foo()",
        "L12: public void Bar()",
    ]),
    ("rust", RUST_SRC, [
        "imports: std::fmt, serde::Serialize",
        "L4: pub struct Foo",
        "L5: field: pub x: i32",
        "L6: field: y: i32",
        "L9: impl Foo",
        "L10: pub fn new() -> Foo",
        "L14: fn helper(&self) -> i32",
    ]),
    ("go", GO_SRC, [
        "package main; imports: github.com/foo/bar",
        "L8: Foo",
        "L9: field: X int",
        "L10: field: y int",
        "L13: Greeter",
        "L14: Hello() string",
        "L17: func (f *Foo) Bar() string",
        "L21: func helper() int",
    ]),
    ("groovy", GROOVY_SRC, [
        "L1: plugins",
        "L2: id 'java'",
        "L5: dependencies",
        "L6: implementation 'com.example:lib:1.0'",
    ]),
    ("markdown", MARKDOWN_SRC, [
        "L1: # Title",
        "L5: ## Section",
    ]),
]


@pytest.mark.parametrize("lang, src, expected", LANGUAGE_CASES, ids=[c[0] for c in LANGUAGE_CASES])
def test_build_digest_contains_expected_lines(lang, src, expected):
    digest = build_digest(src, lang, f"test.{lang}")
    assert digest is not None
    for substring in expected:
        assert substring in digest, f"missing {substring!r} in:\n{digest}"
