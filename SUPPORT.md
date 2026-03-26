# Getting Support for H0NEYP0T-466/linkedin-agent

Welcome to the **LinkedIn Agent** project! This autonomous agent monitors GitHub repositories, generates AI-powered LinkedIn posts, and provides real-time feedback through a terminal-style web interface. We're excited you're here and want to get help!

## 🆘 Available Support Channels

We offer multiple ways to get support:

- **🐛 GitHub Issues**: For bug reports, feature requests, and technical problems
- **💬 GitHub Discussions**: For questions, community help, and general discussions
- **📚 Documentation**: Check our comprehensive system explanation in `you.txt`

## 🐛 GitHub Issues

### When to Use Issues
Use GitHub Issues for:
- **Bug Reports**: Application crashes, unexpected behavior, or broken functionality
- **Feature Requests**: New capabilities or improvements you'd like to see
- **Technical Problems**: Backend service errors, API failures, or deployment issues
- **Code-Related Questions**: Specific implementation concerns about the codebase

### What to Include in Your Issue
To help us resolve your issue quickly, please include:

1. **Clear title** describing the problem
2. **Detailed description** of what happened vs. what you expected
3. **Steps to reproduce** (if applicable)
4. **Environment details**:
   - Operating System
   - Python version (`python --version`)
   - Node.js version (`node --version`)
   - Browser (for frontend issues)
5. **Error messages** with full stack traces
6. **Relevant configuration files** (with sensitive data redacted)
7. **Screenshots** (for UI-related issues)

### Example Issue Structure
```
Title: [Backend] WebSocket connection fails on startup

Description:
When starting the application, the WebSocket connection to the backend fails with error "Connection refused".

Steps to Reproduce:
1. Run `cd backend && source venv/bin/activate`
2. Execute `uvicorn main:app --host 0.0.0.0 --port 8006 --reload`
3. Open browser to http://localhost:5173
4. Observe connection error in terminal UI

Environment:
- OS: Ubuntu 22.04 LTS
- Python: 3.11.9
- Node.js: 18.17.0

Error Output:
[ERROR] Connection failed: [Errno 111] Connection refused
```

## 💬 GitHub Discussions

### When to Use Discussions
Use GitHub Discussions for:
- **General Questions**: How the agent works, usage patterns, or setup guidance
- **Community Help**: Best practices, optimization tips, or workflow suggestions
- **Feature Ideas**: Brainstorming new functionality or use cases
- **Learning & Tutorials**: Questions about understanding or extending the project

### Discussion Categories
We organize discussions into helpful categories:
- **Q&A**: General questions about the project
- **Show and Tell**: Share your implementations or modifications
- **Ideas**: Feature suggestions and brainstorming
- **General**: Other topics related to the project

## 📚 Documentation Resources

Before asking questions, check these resources:

- **[System Overview](you.txt)**: Comprehensive explanation of the LinkedIn Agent architecture and functionality
- **Backend Setup**: Review `backend/run_commands.txt` for environment activation and server startup
- **API Documentation**: Examine `backend/main.py` for available endpoints and WebSocket events
- **Frontend Components**: Check `src/App.tsx` for the main user interface logic

## 🤔 How to Ask a Good Question

### Be Specific and Clear
- Use descriptive titles that clearly state the problem
- Provide context about what you're trying to accomplish
- Mention any research you've already done

### Include Relevant Information
- **What you tried**: Describe your attempted solutions
- **What actually happened**: Be specific about errors or unexpected behavior
- **What you expected**: Explain the desired outcome
- **Your environment**: Include versions and configuration details

### Format Code Properly
```python
# Bad: Inline code without formatting
print("error")

# Good: Properly formatted code block
print("This is properly formatted")
```

### Search First!
Before creating an issue or discussion, search existing ones to avoid duplicates.

## ❌ What NOT to Use Issues For

Please don't create issues for:
- **General Questions**: Use GitHub Discussions instead
- **Usage Questions**: How-to guides belong in Discussions
- **Support Requests**: Community forums are better suited
- **Duplicate Reports**: Search first before posting
- **Personal Data**: Never share credentials, API keys, or personal information
- **Off-Topic Content**: Keep discussions relevant to this project

## ⏰ Response Time Expectations

- **GitHub Issues**: Typically respond within 2-5 business days
- **GitHub Discussions**: Usually reply within 3-7 business days
- **Critical Bugs**: Priority response for security vulnerabilities or major functionality breaks
- **Weekends/Holidays**: Response times may be delayed

## 🤝 Community Guidelines

- **Be Respectful**: Treat all community members with kindness and professionalism
- **Stay On Topic**: Keep discussions relevant to the LinkedIn Agent project
- **Help Others**: Answer questions when you can to build a supportive community
- **Provide Constructive Feedback**: Offer suggestions that help improve the project

---

**Ready to contribute?** Check out our [Contributing Guide](CONTRIBUTING.md) if you're interested in helping develop the project!

*Have fun building with the LinkedIn Agent! 🚀*