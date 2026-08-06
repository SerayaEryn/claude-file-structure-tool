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

TERRAFORM_SRC = b"""resource "aws_instance" "web" {
  ami           = "abc"
  instance_type = "t2.micro"

  tags = {
    Name = "web"
  }
}

module "vpc" {
  source = "./modules/vpc"
}
"""

SCALA_SRC = b"""package com.example

import scala.util.Try
import com.example.util.Helper

trait Greeter {
  def greet(name: String): String
}

object Foo {
  val z: Int = 0
}

case class Bar(a: Int) extends Greeter {
  def greet(name: String) = "hi " + name
  private val secret = 1
}
"""

RUBY_SRC = b"""require 'json'
require_relative './helper'

module M
  class Foo < Bar
    def self.build
      new
    end

    def bar(a)
      a
    end
  end
end
"""

MARKDOWN_SRC = b"""# Title

Some text.

## Section

More text.
"""

LANGUAGE_CASES = [
    ("java", JAVA_SRC, [
        "package com.example; imports: util.Helper",
        "L6-12: public class Foo",
        "L7: field: private int x, y",
        "L8-9: public Foo()",
        "L10-11: public void bar()",
    ]),
    ("kotlin", KOTLIN_SRC, [
        "package com.example; imports: util.List",
        "L5-9: class Foo",
        "L6: field: private val x: Int = 0",
        "L7-8: fun bar()",
    ]),
    ("python", PYTHON_SRC, [
        "imports: none notable (2 stdlib/common)",
        "L5-13: class Foo",
        "L6-7: def __init__(self)",
        "L9-10: def _helper(self)",
        "L12-13: def bar(self)",
    ]),
    ("typescript", TYPESCRIPT_SRC, [
        "imports: ./list",
        "L4-6: interface Greeter",
        "L5: greet(): string",
        "L8-13: class Foo",
        "L9: field: private x: number = 0",
        "L10: field: #secret: number = 0",
        "L11-12: bar(): void",
        "L15-17: const make = (): Foo =>",
    ]),
    ("tsx", TSX_SRC, [
        "imports: react",
        "L3-5: function Card(props: { title: string })",
    ]),
    ("javascript", JAVASCRIPT_SRC, [
        "imports: ./helper",
        "L4-8: class Foo",
        "L5: field: #secret = 0",
        "L6-7: bar()",
        "L10-11: function baz()",
        "L13-15: const make = () =>",
    ]),
    ("csharp", CSHARP_SRC, [
        "namespace MyApp; imports: MyApp.Utils",
        "L4-16: namespace MyApp",
        "L6-15: public class Foo",
        "L8: field: private int x, y",
        "L9-11: public Foo()",
        "L12-14: public void Bar()",
    ]),
    ("rust", RUST_SRC, [
        "imports: std::fmt, serde::Serialize",
        "L4-7: pub struct Foo",
        "L5: field: pub x: i32",
        "L6: field: y: i32",
        "L9-17: impl Foo",
        "L10-12: pub fn new() -> Foo",
        "L14-16: fn helper(&self) -> i32",
    ]),
    ("go", GO_SRC, [
        "package main; imports: github.com/foo/bar",
        "L8-11: Foo",
        "L9: field: X int",
        "L10: field: y int",
        "L13-15: Greeter",
        "L14: Hello() string",
        "L17-19: func (f *Foo) Bar() string",
        "L21-23: func helper() int",
    ]),
    ("terraform", TERRAFORM_SRC, [
        'L1-8: resource "aws_instance" "web"',
        'L10-12: module "vpc"',
    ]),
    ("scala", SCALA_SRC, [
        "package com.example; imports: util.Helper",
        "L6-8: trait Greeter",
        "L7: def greet(name: String): String",
        "L10-12: object Foo",
        "L11: field: val z: Int = 0",
        "L14-17: case class Bar(a: Int) extends Greeter",
        "L15: def greet(name: String)",
        "L16: field: private val secret = 1",
    ]),
    ("ruby", RUBY_SRC, [
        "imports: json, ./helper",
        "L4-14: module M",
        "L5-13: class Foo < Bar",
        "L6-8: def self.build",
        "L10-12: def bar(a)",
    ]),
    ("groovy", GROOVY_SRC, [
        "L1-5: plugins",
        "L2-3: id 'java'",
        "L5-8: dependencies",
        "L6-7: implementation 'com.example:lib:1.0'",
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


def test_terraform_block_header_is_collapsed_not_full_body():
    # Regression guard: if the grammar's body-detection ever breaks, _extract_sig
    # falls back to node.end_byte and emits the *entire block* (attributes
    # included) as one line instead of just the header - a plain substring
    # check wouldn't catch that since the short header is a prefix of the
    # failure-mode output too.
    digest = build_digest(TERRAFORM_SRC, "terraform", "test.tf")
    lines = digest.split("\n")
    assert 'L1-8: resource "aws_instance" "web"' in lines
    assert "ami" not in digest
    assert "instance_type" not in digest
