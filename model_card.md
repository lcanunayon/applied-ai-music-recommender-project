# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

Music4u 1.0

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

This recomender system suggests about 5 songs from a selection based off users preferred genre, mood, energy, etc. It is mostly for classroom purposes, not for real users.

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

The algorithm works by scoring songs based on a users preferred song profile and songs with their attributes. It ranks these songs and their score based on how close they are to the users preferrences, and sorts all of these songs in descending order of score. The top k (usually 5) songs are picked and recommended to the user.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

18 songs are in songs.csv. I added a couple more songs to the original. Some genres represented is rock, pop, lofi, r&b. Some moods are happy, sad, hype, chill, focused, etc. This taste mostly reflects a pop taste as there is mostly pop type songs and the user profile is pop as well.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

My recommender works well for differentiates similar songs and giving them a concise and accurate ranking for them. It is simple and easy to use, and it served user profiles extremely well.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

Some of the songs dont seem to be right by intuitition, but they are mathematically correct, which is not so much an issue. The real issue is a catalog representation bias, as a genre like lofi has a more differentiated and quality recommendation compared to the other genres other than pop, which is slightly less differentiated. Lofi song matching is more fleshed out and has more songs to recommend to the user.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

I tried multiple user profiles, making sure that the results matched expectations from the songs I already have. I also wrote tests for the scoring logic to make sure the scoring was accurate and expected.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

I would improve this recommender for adding other users and being able to recommend songs based on the whole group and all of their attributes combined. Also, I would try to add more features like lyric themes and sharing of recommendations to others.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

Id say the biggest learning moment I learned during this project is using AI to explain to me a system and algorithm so I could understand it better and give it implementation and features that I wouldnt have thought otherwise. What surprised me about this system is how accurate it was, especially with the various fields that songs could be rated on. AI tools helped me in this learning aspect, but I had to double check the AI when creating actual logic for the app and ideas. I thought real music recommenders were not as complicated as this, and for a 1% version for something like what Spotify uses, I feel that this can pretty accurately rank a lot of songs already. I was surprised this small algorithm still felt like a full fledged recommender. I think human judgement still matters with intuitive grouping of songs in specific genres, as some fields may sway one result and put a song where it really should not be. If i extended this project, I would definitely try to add a group function with real users, with a UI element.
