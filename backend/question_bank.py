"""
backend/question_bank.py
-------------------------
Static fallback questions for every category. These serve two purposes:

1. Reliability: if the local LLM is slow, unreachable, or returns junk,
   the app can still hand the candidate a solid, pre-vetted question
   instead of crashing or stalling.
2. Variety floor: ensures every category has at least a baseline set of
   well-known, realistic placement questions even on a first run.

The InterviewEngine tries the LLM first and falls back to these on error.
"""

import random

FALLBACK_QUESTIONS: dict[str, list[str]] = {
    "Python": [
        "What is the difference between a list and a tuple in Python?",
        "Explain the difference between deep copy and shallow copy.",
        "What are Python decorators and where have you used one?",
        "How does Python's garbage collection work?",
        "What is the difference between '==' and 'is' in Python?",
    ],
    "Java": [
        "What is the difference between an abstract class and an interface in Java?",
        "Explain JVM, JRE, and JDK.",
        "What is method overloading vs method overriding?",
        "What are checked and unchecked exceptions in Java?",
        "Explain the concept of garbage collection in Java.",
    ],
    "Data Structures": [
        "What is the difference between an array and a linked list?",
        "Explain how a hash table handles collisions.",
        "What is the time complexity of inserting into a balanced binary search tree?",
        "How does a stack differ from a queue, and where would you use each?",
        "Explain how a binary search algorithm works and its time complexity.",
    ],
    "DBMS": [
        "What is normalization and why is it important?",
        "Explain the difference between a primary key and a foreign key.",
        "What is the difference between DELETE, TRUNCATE, and DROP?",
        "What are ACID properties in a database transaction?",
        "Explain the difference between a clustered and a non-clustered index.",
    ],
    "SQL": [
        "What is the difference between INNER JOIN and LEFT JOIN?",
        "Write a query to find the second highest salary from an Employees table.",
        "What is the difference between WHERE and HAVING clauses?",
        "What is a subquery, and when would you use one?",
        "Explain GROUP BY with an example use case.",
    ],
    "Operating Systems": [
        "What is the difference between a process and a thread?",
        "Explain deadlock and one way to prevent it.",
        "What is virtual memory and why is it used?",
        "Explain the difference between paging and segmentation.",
        "What is a context switch?",
    ],
    "Computer Networks": [
        "What is the difference between TCP and UDP?",
        "Explain the OSI model layers briefly.",
        "What happens when you type a URL into a browser and press enter?",
        "What is the difference between a router and a switch?",
        "Explain DNS and why it is needed.",
    ],
    "Machine Learning": [
        "What is the difference between supervised and unsupervised learning?",
        "Explain overfitting and how you would prevent it.",
        "What is the bias-variance tradeoff?",
        "How does a confusion matrix help evaluate a classification model?",
        "What is the difference between bagging and boosting?",
    ],
    "Generative AI": [
        "What is the difference between a Large Language Model and a traditional ML model?",
        "Explain what 'prompt engineering' means with an example.",
        "What is Retrieval-Augmented Generation (RAG) and why is it used?",
        "What is the difference between fine-tuning and prompting an LLM?",
        "What are embeddings, and how are they used in semantic search?",
    ],
    "Project-Based": [
        "Walk me through the architecture of your most recent academic or personal project.",
        "What was the most challenging technical problem you solved in your project, and how?",
        "If you had to scale your project to 10x the users, what would you change?",
        "What trade-offs did you make while building your project, and why?",
        "How did you test your project before considering it complete?",
    ],
    "HR": [
        "Tell me about yourself.",
        "What are your greatest strengths and weaknesses?",
        "Why should we hire you over other MCA candidates?",
        "Describe a time you worked under pressure or a tight deadline.",
        "Where do you see yourself in the next three years?",
    ],
}


def get_fallback_question(category: str, already_asked: list[str]) -> str:
    """
    Return a fallback question for a category that hasn't been asked yet
    in this session. If all fallback questions are exhausted, recycle
    randomly rather than erroring out.
    """
    pool = FALLBACK_QUESTIONS.get(category, ["Tell me about a technical concept you find interesting."])
    unused = [q for q in pool if q not in already_asked]
    return random.choice(unused) if unused else random.choice(pool)
