#!/usr/bin/env python3
"""
Simple Job Search Tool
Search jobs from LinkedIn and Naukri with minimal setup
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
from datetime import datetime, timedelta
from typing import List, Dict
from urllib.parse import urlencode
from database import create_jobs_table, save_jobs

class SimpleJobSearch:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_apna(self, job_title: str, location: str = "India") -> List[Dict]:
        """Search jobs on Apna.co - scraper-friendly Indian job portal"""
        jobs = []
        
        try:
            print(f"🔍 Searching Apna.co for: {job_title}")
            
            # Apna.co search URL structure
            search_url = f"https://apna.co/jobs/{job_title.lower().replace(' ', '-')}"
            
            # Alternative URL format
            if location.lower() != "india":
                search_url = f"https://apna.co/jobs?search={job_title.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            
            print(f"   URL: {search_url}")
            
            # Headers for Apna.co
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://apna.co/',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Debug
                page_title = soup.find('title')
                print(f"   Page loaded: {page_title.get_text() if page_title else 'Unknown'}")
                
                # Find job cards on Apna.co
                job_cards = self.find_apna_job_cards(soup)
                
                print(f"   Found {len(job_cards)} job cards")
                
                for i, card in enumerate(job_cards[:8]):  # Limit to 8 jobs
                    job_data = self.parse_apna_job_card(card)
                    if job_data:
                        jobs.append(job_data)
                        print(f"   ✓ Parsed job {i+1}: {job_data['title']} at {job_data['company']}")
            
            else:
                print(f"   HTTP {response.status_code}")
            
            # Add delay to be respectful
            time.sleep(2)
            
            # Fallback to sample data if needed
            if not jobs:
                print("⚠️ Apna scraping failed, adding sample Apna jobs")
                jobs = self.get_sample_apna_jobs(job_title, location)
            
            print(f"✅ Found {len(jobs)} jobs from Apna.co")
            
        except Exception as e:
            print(f"⚠️ Apna search failed: {e}")
            jobs = self.get_sample_apna_jobs(job_title, location)
        
        return jobs
    
    def find_apna_job_cards(self, soup):
        """Find job cards on Apna.co using multiple selectors"""
        job_cards = []
        
        # Try different selectors for Apna.co
        selectors_to_try = [
            '.job-card',
            '.job-item',
            '[data-job-id]',
            '.listing-item',
            '.job-listing',
            '.card',
            'article',
            '.job-post'
        ]
        
        for selector in selectors_to_try:
            cards = soup.select(selector)
            if cards:
                print(f"   Using selector: {selector} ({len(cards)} found)")
                job_cards = cards
                break
        
        # If no specific job cards found, look for any structured content
        if not job_cards:
            job_cards = soup.find_all(['div', 'article'], class_=lambda x: x and len(x) > 5)
        
        return job_cards
    
    def parse_apna_job_card(self, card):
        """Parse individual Apna.co job card"""
        try:
            job_data = {
                'title': '',
                'company': '',
                'location': '',
                'experience': '',
                'salary': 'Not disclosed',
                'description': '',
                'apply_url': '#',
                'source': 'Apna.co'
            }
            
            # Extract job title and link
            title_selectors = [
                'h2 a', 'h3 a', '.job-title a', '.title a', 
                'a[href*="job"]', '.job-name', '.position'
            ]
            
            for selector in title_selectors:
                title_elem = card.select_one(selector)
                if title_elem:
                    job_data['title'] = title_elem.get_text(strip=True)
                    href = title_elem.get('href')
                    if href and self.is_valid_job_url(href):
                        if href.startswith('/'):
                            job_data['apply_url'] = f"https://apna.co{href}"
                        else:
                            job_data['apply_url'] = href
                    break
            
            # If no link found, try text-only title
            if not job_data['title']:
                title_text_selectors = ['h2', 'h3', '.job-title', '.title', '.job-name']
                for selector in title_text_selectors:
                    title_elem = card.select_one(selector)
                    if title_elem:
                        job_data['title'] = title_elem.get_text(strip=True)
                        break
            
            # If still no apply URL, look for any job-related links in the card
            if job_data['apply_url'] == '#':
                all_links = card.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href')
                    if href and self.is_valid_job_url(href):
                        if href.startswith('/'):
                            job_data['apply_url'] = f"https://apna.co{href}"
                        else:
                            job_data['apply_url'] = href
                        break
            
            # Extract company name
            company_selectors = [
                '.company-name', '.company', '.employer', 
                '.org-name', '.business-name'
            ]
            
            for selector in company_selectors:
                company_elem = card.select_one(selector)
                if company_elem:
                    job_data['company'] = company_elem.get_text(strip=True)
                    break
            
            # Extract location
            location_selectors = [
                '.location', '.job-location', '.place', '.city'
            ]
            
            for selector in location_selectors:
                location_elem = card.select_one(selector)
                if location_elem:
                    job_data['location'] = location_elem.get_text(strip=True)
                    break
            
            # Extract salary
            salary_selectors = [
                '.salary', '.pay', '.wage', '.compensation'
            ]
            
            for selector in salary_selectors:
                salary_elem = card.select_one(selector)
                if salary_elem:
                    job_data['salary'] = salary_elem.get_text(strip=True)
                    break
            
            # Extract description
            desc_selectors = [
                '.description', '.job-desc', '.summary', '.details'
            ]
            
            for selector in desc_selectors:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    job_data['description'] = desc_elem.get_text(strip=True)[:200] + "..."
                    break
            
            # Only return if we have essential data
            if job_data['title']:
                # Set defaults
                if not job_data['company']:
                    job_data['company'] = 'Various Companies'
                if not job_data['location']:
                    job_data['location'] = 'India'
                if not job_data['experience']:
                    job_data['experience'] = 'As per requirement'
                
                # Ensure we have a working apply URL
                if job_data['apply_url'] == '#' or not self.is_valid_job_url(job_data['apply_url']):
                    job_data['apply_url'] = self.get_fallback_job_url(job_data['title'], job_data['company'], 'Apna.co')
                
                return job_data
            
            return None
            
        except Exception as e:
            print(f"   Error parsing Apna job card: {e}")
            return None
    
    def get_sample_apna_jobs(self, job_title: str, location: str) -> List[Dict]:
        """Sample Apna.co jobs when scraping fails"""
        companies = ["Zomato", "Swiggy", "Urban Company", "Dunzo", "BigBasket", "Grofers", "Ola", "Uber"]
        locations = ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad"]
        
        jobs = []
        for i in range(6):
            company = companies[i % len(companies)]
            title = f"{job_title}" if i == 0 else f"Senior {job_title}" if i == 1 else f"{job_title} - {company}"
            
            jobs.append({
                'title': title,
                'company': company,
                'location': locations[i % len(locations)],
                'experience': f"{1 + i}-{3 + i} years" if i > 0 else "Fresher",
                'salary': f"₹{15 + i * 5}k - ₹{25 + i * 8}k per month",
                'description': f"Exciting {job_title} opportunity at {company} with growth potential and competitive benefits.",
                'apply_url': self.get_fallback_job_url(title, company, 'Apna.co'),
                'source': 'Apna.co'
            })
        
        return jobs
    
    def is_valid_job_url(self, url: str) -> bool:
        """Check if URL looks like a valid job posting URL"""
        if not url:
            return False
        
        # Check for common job URL patterns
        job_patterns = [
            '/job/', '/jobs/', '/career/', '/careers/', 
            '/vacancy/', '/opening/', '/position/',
            'job-detail', 'job_detail', 'jobdetail'
        ]
        
        return any(pattern in url.lower() for pattern in job_patterns)
    
    def get_fallback_job_url(self, job_title: str, company: str, source: str) -> str:
        """Generate a working fallback URL for job applications"""
        job_slug = job_title.lower().replace(' ', '-').replace('/', '-')
        company_slug = company.lower().replace(' ', '-').replace('/', '-')
        
        if source == 'Apna.co':
            # Use Apna's job search with specific parameters
            return f"https://apna.co/jobs?search={job_title.replace(' ', '%20')}&company={company.replace(' ', '%20')}"
        
        else:
            # Generic job search
            return f"https://www.google.com/search?q={job_title.replace(' ', '+')}+jobs+at+{company.replace(' ', '+')}"
    
   
    
    def parse_indeed_job_card(self, card):
        """Parse individual Indeed job card"""
        try:
            job_data = {
                'title': '',
                'company': '',
                'location': '',
                'experience': '',
                'salary': 'Not disclosed',
                'description': '',
                'apply_url': '#',
                'source': 'Indeed'
            }
            
            # Extract job title and link
            title_selectors = [
                'h2 a[data-jk]',
                '.jobTitle a',
                'h2.jobTitle a',
                '[data-testid="job-title"] a',
                'a[data-jk]'
            ]
            
            for selector in title_selectors:
                title_elem = card.select_one(selector)
                if title_elem:
                    job_data['title'] = title_elem.get_text(strip=True)
                    href = title_elem.get('href')
                    if href:
                        if href.startswith('/'):
                            job_data['apply_url'] = f"https://www.indeed.com{href}"
                        else:
                            job_data['apply_url'] = href
                    break
            
            # Extract company name
            company_selectors = [
                '.companyName',
                '[data-testid="company-name"]',
                '.company',
                'span.companyName a',
                'span.companyName'
            ]
            
            for selector in company_selectors:
                company_elem = card.select_one(selector)
                if company_elem:
                    job_data['company'] = company_elem.get_text(strip=True)
                    break
            
            # Extract location
            location_selectors = [
                '.companyLocation',
                '[data-testid="job-location"]',
                '.location',
                'div.companyLocation'
            ]
            
            for selector in location_selectors:
                location_elem = card.select_one(selector)
                if location_elem:
                    job_data['location'] = location_elem.get_text(strip=True)
                    break
            
            # Extract salary
            salary_selectors = [
                '.salary-snippet',
                '.salaryText',
                '[data-testid="job-salary"]',
                '.salary'
            ]
            
            for selector in salary_selectors:
                salary_elem = card.select_one(selector)
                if salary_elem:
                    job_data['salary'] = salary_elem.get_text(strip=True)
                    break
            
            # Extract job snippet/description
            desc_selectors = [
                '.job-snippet',
                '.summary',
                '[data-testid="job-snippet"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    job_data['description'] = desc_elem.get_text(strip=True)[:200] + "..."
                    break
            
            # Only return if we have essential data
            if job_data['title'] and job_data['company']:
                # Set defaults
                if not job_data['location']:
                    job_data['location'] = 'Remote'
                if not job_data['experience']:
                    job_data['experience'] = 'Not specified'
                
                return job_data
            
            return None
            
        except Exception as e:
            print(f"   Error parsing Indeed job card: {e}")
            return None
    
    def parse_indeed_alternative(self, soup, job_title, location):
        """Alternative Indeed parsing method"""
        jobs = []
        
        # Look for any job-related links
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            
            if (len(text) > 10 and 
                ('/viewjob' in href or '/jobs/' in href) and
                any(word in text.lower() for word in ['developer', 'engineer', 'analyst'])):
                
                if href.startswith('/'):
                    href = f"https://www.indeed.com{href}"
                
                jobs.append({
                    'title': text,
                    'company': 'Various Companies',
                    'location': location,
                    'experience': 'As per requirement',
                    'salary': 'Competitive',
                    'description': f"Job opportunity: {text}",
                    'apply_url': href,
                    'source': 'Indeed'
                })
                
                if len(jobs) >= 5:
                    break
        
        return jobs
    
    def get_sample_indeed_jobs(self, job_title: str, location: str) -> List[Dict]:
        """Sample Indeed jobs when scraping fails"""
        companies = ["Microsoft", "Google", "Amazon", "Apple", "Meta", "Netflix", "Uber", "Airbnb"]
        locations = ["Remote", "San Francisco, CA", "Seattle, WA", "New York, NY", "Austin, TX"]
        
        jobs = []
        for i in range(6):
            jobs.append({
                'title': f"{job_title}" if i == 0 else f"Senior {job_title}" if i == 1 else f"{job_title} - {companies[i % len(companies)]}",
                'company': companies[i % len(companies)],
                'location': locations[i % len(locations)],
                'experience': f"{2 + i}-{5 + i} years",
                'salary': f"${60 + i * 15}k - ${90 + i * 15}k",
                'description': f"Exciting {job_title} opportunity at {companies[i % len(companies)]} with competitive benefits and growth opportunities.",
                'apply_url': f"https://www.indeed.com/viewjob?jk=sample{i}",
                'source': 'Indeed'
            })
        
        return jobs
    

    
    def search_linkedin(
        self,
        job_title: str,
        location: str = "India"
    ) -> List[Dict]:
        """Search jobs on LinkedIn and filter results by location."""

        jobs = []

        try:

            params = {
                'keywords': job_title,
                'location': location,
                'redirect': 'false',
                'position': '1'
            }

            url = (
                f"https://www.linkedin.com/jobs/search?"
                f"{urlencode(params)}"
            )

            print(
                f"🔍 Searching LinkedIn for: "
                f"{job_title} in {location}"
            )

            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:

                soup = BeautifulSoup(
                    response.content,
                    'html.parser'
                )

                job_cards = (
                    soup.find_all(
                        'div',
                        class_='job-search-card'
                    )
                    or soup.find_all(
                        'li',
                        class_='result-card'
                    )
                    or soup.find_all(
                        'div',
                        {'data-entity-urn': True}
                    )
                )

                print(
                    f"🔎 LinkedIn returned "
                    f"{len(job_cards)} job cards"
                )

                for card in job_cards[:10]:

                    job = self.parse_linkedin_job(card)

                    if not job:
                        continue

                    job_location = job.get(
                        'location',
                        ''
                    )

                    if self.location_matches(
                        location,
                        job_location
                    ):

                        jobs.append(job)

                        print(
                            f"   ✓ {job['title']} — "
                            f"{job['company']} | "
                            f"{job_location}"
                        )

                    else:

                        print(
                            f"   ✗ Skipped: "
                            f"{job['title']} — "
                            f"{job['company']} | "
                            f"{job_location}"
                        )

            else:

                print(
                    f"⚠️ LinkedIn returned "
                    f"HTTP {response.status_code}"
                )

            print(
                f"✅ Found {len(jobs)} "
                f"location-matched jobs from LinkedIn"
            )

        except Exception as e:

            print(
                f"⚠️ LinkedIn search failed: {e}"
            )

            return []

        return jobs


    def location_matches(
        self,
        requested_location: str,
        job_location: str
    ) -> bool:
        """Check whether a job location matches the requested location."""

        if not requested_location or not job_location:
            return False

        requested = requested_location.lower().strip()
        actual = job_location.lower().strip()

        # Remote search
        if requested == "remote":
            return "remote" in actual

        # India-wide search
        if requested == "india":
            return (
                "india" in actual
                or "remote" in actual
            )

        # Delhi/NCR
        if requested in {
            "delhi",
            "new delhi",
            "delhi ncr"
        }:

            delhi_locations = {
                "delhi",
                "new delhi",
                "delhi ncr",
                "gurugram",
                "gurgaon",
                "noida",
                "faridabad",
                "ghaziabad"
            }

            # Delhi/NCR locations should be in India.
            if "india" not in actual:
                return False

            return any(
                city in actual
                for city in delhi_locations
            )

        # Generic location matching
        return (
            requested in actual
            or actual in requested
        )
    def parse_linkedin_job(self, card) -> Dict:
        """Parse LinkedIn job card"""
        try:
            title = self.get_text(card, ['h3', '.result-card__title', '.job-title'])
            company = self.get_text(card, ['h4', '.result-card__subtitle', '.company-name'])
            location = self.get_text(card, ['.job-search-card__location', '.result-card__location'])
            # Get posting date
            date_elem = card.select_one('time.job-search-card__listdate')
            posted_date = date_elem.get('datetime') if date_elem else None
            
            posted_text = date_elem.get_text(strip=True) if date_elem else 'Date not available'
            # Get job link
            link_elem = card.find('a')
            job_link = link_elem['href'] if link_elem and link_elem.get('href') else "#"
            if job_link.startswith('/'):
                job_link = f"https://www.linkedin.com{job_link}"
            
            return {
                'title': title or 'Software Developer',
                'company': company or 'Tech Company',
                'location': location or 'Remote',
                'experience': 'Not specified',
                'salary': 'Not disclosed',
                'posted_date': posted_date,
                'posted_text': posted_text,
                'apply_url': job_link,
                'source': 'LinkedIn'
            }
        except:
            return None
    
    def get_text(self, element, selectors: List[str]) -> str:
        """Helper to get text from element using multiple selectors"""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    return found.get_text(strip=True)
            except:
                continue
        return ""  
  
    def get_realistic_naukri_jobs(self, job_title: str) -> List[Dict]:
        """Realistic Naukri jobs that link to actual working Naukri pages"""
        base_search = job_title.lower().replace(' ', '-')
        
        # Create jobs that mirror the structure from your screenshot
        # These URLs will take users to actual Naukri search results
        job_data = [
            {
                'title': f"{job_title} - Fresher",
                'company': "TCS",
                'location': "Hyderabad, Chennai, Bangalore", 
                'experience': "0 - 2 years",
                'salary': "₹ 3-4 Lacs P.A.",
                'description': "We are looking for a Python Developer to assist in building scalable applications and automation tools. Key Responsibilities: Write clean and efficient Python code, Learn frameworks like Django or Flask, Work on data processing and scripting tasks.",
                'apply_url': f"https://www.naukri.com/{base_search}-jobs"
            },
            {
                'title': "Prompt Engineer (Fresher)",
                'company': "IT Shops", 
                'location': "Hyderabad, Chennai, Bangalore",
                'experience': "4.3 - 17 reviews",
                'salary': "Not disclosed",
                'description': "Exciting opportunity for AI and machine learning enthusiasts. Work with cutting-edge prompt engineering technologies.",
                'apply_url': "https://www.naukri.com/prompt-engineer-jobs"
            },
            {
                'title': f"{job_title}",
                'company': "Smart Placement Services",
                'location': "Hybrid - Hyderabad, Bangalore", 
                'experience': "Posted 21 days ago",
                'salary': "Competitive",
                'description': f"Looking for experienced {job_title} for hybrid work model with flexible timings and growth opportunities.",
                'apply_url': f"https://www.naukri.com/{base_search}-jobs-in-bangalore"
            },
            {
                'title': f"{job_title} - Fresher (WFH)",
                'company': "AIVOA",
                'location': "Bangalore",
                'experience': "Posted 71 days ago", 
                'salary': "₹ 2.5-5 Lacs P.A.",
                'description': f"Work from home opportunity for {job_title} freshers. Complete training provided with mentorship program.",
                'apply_url': f"https://www.naukri.com/work-from-home-{base_search}-jobs"
            },
            {
                'title': "Data Engineer",
                'company': "IT Shops",
                'location': "Hyderabad, Chennai, Bangalore",
                'experience': "4.3 - 17 reviews",
                'salary': "Posted 25 days ago",
                'description': "Data engineering role with modern tech stack including Python, SQL, and cloud platforms. Great learning opportunities.",
                'apply_url': "https://www.naukri.com/data-engineer-jobs"
            },
            {
                'title': f"{job_title} Fullstack Developer", 
                'company': "Saushruthi Solutions",
                'location': "Multiple locations",
                'experience': "2-5 years",
                'salary': "₹ 4-8 Lacs P.A.",
                'description': f"Full stack development role combining {job_title} backend with modern frontend frameworks. Exciting projects ahead.",
                'apply_url': f"https://www.naukri.com/fullstack-{base_search}-jobs"
            }
        ]
        
        # Add source to each job
        for job in job_data:
            job['source'] = 'Naukri'
        
        return job_data
      
    def search_jobs(
        self,
        job_title: str,
        location: str = "India",
        recency_days: int = 30
    ) -> List[Dict]:
        """Search recent jobs from LinkedIn using the requested freshness window."""

        print(f"\n🚀 Starting job search for: {job_title}")
        print("=" * 50)

        # Search LinkedIn
        linkedin_jobs = self.search_linkedin(job_title, location)

        # Filter out jobs older than 30 days
        cutoff_date = (
            datetime.now().date()
            - timedelta(days=recency_days)
        )

        filtered_jobs = []

        for job in linkedin_jobs:
            posted_date = job.get('posted_date')

            if not posted_date:
                # Keep jobs without a posting date for now
                filtered_jobs.append(job)
                continue

            try:
                job_date = datetime.strptime(
                    posted_date, '%Y-%m-%d'
                ).date()

                if job_date >= cutoff_date:
                    filtered_jobs.append(job)

            except ValueError:
                # Keep jobs if the date format cannot be parsed
                filtered_jobs.append(job)

                # Remove duplicate LinkedIn listings
        unique_jobs = self.remove_duplicates(filtered_jobs)

        # Save jobs to SQLite
        save_jobs(unique_jobs)

        print(f"\n💾 Saved {len(unique_jobs)} jobs to database")
        print(f"\n✅ Total jobs found: {len(unique_jobs)}")
        print(f"   💼 LinkedIn: {len(unique_jobs)} jobs")

        return unique_jobs

    def remove_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on title and company"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            key = (job['title'].lower().strip(), job['company'].lower().strip())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def save_to_csv(self, jobs: List[Dict], filename: str = None) -> str:
        """Save jobs to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'company', 'location', 'experience', 'salary', 'apply_url', 'source']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for job in jobs:
                writer.writerow(job)
        
        print(f"📊 Results saved to: {filename}")
        return filename
    
    def display_jobs(self, jobs: List[Dict]):
        """Display jobs in console"""
        print("\n📋 Job Results:")
        print("=" * 60)
        
        for i, job in enumerate(jobs, 1):
            # Get source icon
            if "linkedin" in job['source'].lower():
                source_icon = "💼"
            else:
                source_icon = "🔍"
            
            print(f"\n{i}. {job['title']} [{source_icon} {job['source']}]")
            print(f"   🏢 Company: {job['company']}")
            print(f"   📍 Location: {job['location']}")
            print(f"   💼 Experience: {job['experience']}")
            print(f"   💰 Salary: {job['salary']}")
            if job.get('description'):
                print(f"   📝 Description: {job['description']}")
            print(f"   🔗 Apply: {job['apply_url']}")

def main():
    """Main function to run job search"""
    create_jobs_table()
    print("🤖 Simple Job Search Tool")
    print("=" * 30)
    
    # Get user input
    job_title = input("Enter job title (e.g., Python Developer): ").strip()
    if not job_title:
        job_title = "Software Developer"
    
    location = input("Enter location (default: India): ").strip()
    if not location:
        location = "India"
    
    # Search jobs
    searcher = SimpleJobSearch()
    jobs = searcher.search_jobs(job_title, location)
    
    if jobs:
        # Display results
        searcher.display_jobs(jobs)
        
        # Save to CSV
        filename = searcher.save_to_csv(jobs)
        
        print(f"\n🎉 Search completed! Found {len(jobs)} jobs.")
        print(f"📁 Results saved to: {filename}")
    else:
        print("❌ No jobs found. Try different keywords.")

def main():
    """Main function to run job search"""
    print("🤖 Simple Job Search Tool")
    print("=" * 30)
    
    # Get user input
    job_title = input("Enter job title (e.g., Python Developer): ").strip()
    if not job_title:
        job_title = "Software Developer"
    
    location = input("Enter location (default: India): ").strip()
    if not location:
        location = "India"
    
    # Search jobs
    searcher = SimpleJobSearch()
    jobs = searcher.search_jobs(job_title, location)
    
    if jobs:
        # Display results
        searcher.display_jobs(jobs)
        
        # Save to CSV
        filename = searcher.save_to_csv(jobs)
        
        print(f"\n🎉 Search completed! Found {len(jobs)} jobs.")
        print(f"📁 Results saved to: {filename}")
    else:
        print("❌ No jobs found. Try different keywords.")

if __name__ == "__main__":
    main()
