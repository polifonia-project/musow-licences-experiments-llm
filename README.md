# musoW terms KG

## Task 1: find links including licences and terms and conditions from a web page

### Prompt engineering

BEFORE

	Task 1: find links including licences and terms and conditions from a web page
	SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content.
	USER: Find the link to the pages describing licences, privacy policies, or terms of use of the content in the following HTML source code. Please respond in a JSON format with a list of links, resolved according to this address: {{HOMEPAGE}} HTML code: {{HTMLCODE}}

AFTER

    Task 1: find links including licences and terms and conditions from a web page
    SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content.
    USER: Find the link to the pages describing licences, privacy policies, or terms of use of the content in the following HTML source code. Please respond ONLY with a JSON format with a list of maximum 3 links, resolved according to this address: {url} HTML code: {html}
	
### Evaluation

- Are there any links returned? Yes/No
- Is the returned well-formed JSON? Yes/No
- Are the links relevant? Likert-Scale (definitely not -- surely yes)

## Task 2: Extract copyright and licences

### Prompt engineering

BEFORE

	Task 2: Extract copyright and licences
	SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content.
	USER: Please list the licences and copyright owners named in the following HTML code. Format the answer in JSON with two fields, 'copyright' and 'licences'. {{HTMLCODEE}}

AFTER

	Task 2: Extract copyright, licences, and terms of use
	SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content and express it in JSON format.
	USER: Please list the licences, copyright owners, and terms and conditions mentioned in the following text. Respond only with a JSON object with 3 fields, 'copyright', 'licences', and 'terms and conditions'. The text is: {text}

### Evaluation

- Is the returned well-formed JSON?
- Did the LLM found any copyright information?
- Did the LLM found any licence information?
- Did the LLM found any terms and condition information?

on a sample

- Is the copyright information correct?
- Is the licence information correct?
- Is the terms and condition information correct? (future work)



## Task 3: Link licences to library codes

BEFORE

	Task 3: Link licences to the licence library codes
	SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. You also know how to find information on a web page by reading its HTML content. You are also proficient in reading YAML files.
	USER: Given the following list of licences, can you tell me to which licence the following description refers to: {{LICENCEEXPR}} {{YAML}}

AFTER

	Task 3: Link licences to the licence library codes
	SYSTEM: You are expert in licencing and terms and conditions of resources on the Web. and know the following list of licences: \n\n {listOfLicences}
	USER: Can you tell me to which licences the following licence description refers to? The description is  {description} -- Please respond by only reporting the selected licences from the list or 'NONE' if none is found

### Evaluation

- -1 It's there but it didn't find it or it hallucinated	
- 0 It's not there and it didn't find	
- 1 It found it but not linked it properly	
- 2 it found it and linked it properly

- How many correct decisions are made? (all except -1)
- How many licences are correctly not found? (0)
- How many licences are correctly found? (1 and 2)
- How many licences are linked to the list? (2)







# musow-licences
