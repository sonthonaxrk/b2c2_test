# B2C2 Exercise

This is my [Rollo's] attempt at this task.

However, I refuse to do technical tests if I do not get anything out of it myself.
The way I see it, this is my personal development time.


## Why is the API client so complicated?

In this exercise I tried to solve a few different problems that pertain to IPC between
microservices; namely these:

	1. API clients are repetitive to build;

	2. People frequently use OpenAPI as documentation rather than a formal specification;

	3. It is difficult to enforce formal specifications in Python without expensive runtime checking.

Some companies have developed in house tools to solve these problems. For example,
Google developed ProtocolBuffers and GRPC to solve these issues. But the developer
experience is poor when using Python.

My API client's base-class automatically creates typed methods from a pseudo-OpenAPI
definition. This uses a formal definition of an API to save time. However MyPy will not
work with dynamically created classes; and for MyPy to recognise metaprogramming, a
plug-in is needed (this is how dataclasses, attrs, and ctypes are supported in MyPy).

With this plug-in you can use static analysis to verify you are using the API
correctly (as long as the OpenAPI specification is correct).

## Why am I using the Trade API not the Order API?

I can see the Trade API is deprecated in favour of the Order API; I would rather use
what's defined in the task's specification and use the Trade API, as you might be running
automated tests to check this work.



## GUI Design

Stateful elements:

I am going to make the assumption that instruments won't change during a session.

Getting instruments will be part of the startup procedure of the client.

These will be displayed in some sort of selector.
