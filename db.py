import tornado.gen
import psycopg2
import momoko

import config

class MomokoDB:
	db = momoko.Pool(dsn='dbname=%s user=%s' % (config.db.database, config.db.user), size=2)

	@tornado.gen.coroutine
	def execute(self, query, *args):
		result = yield momoko.Op(self.db.execute, query, args, cursor_factory=psycopg2.extras.DictCursor)
		return result

	@tornado.gen.coroutine
	def create_user(self, user):
		query = 'INSERT INTO users (github_id, username, access_token, is_mentor) VALUES (%s, %s, %s, %s);'
		yield self.execute(query, user['id'], user['login'], user['access_token'], 0)

	@tornado.gen.coroutine
	def create_mentorship(self, mentee, mentor):
		mentee_claimed = yield self.get_mentor(mentee['github_id'])
		if mentor['is_mentor'] and not mentee['is_mentor'] and not mentee_claimed:
			query = 'INSERT INTO mentorships(mentee_id, mentor_id) VALUES (%s, %s);'
			yield self.execute(query, mentee['github_id'], mentor['github_id'])

	@tornado.gen.coroutine
	def update_access_token(self, user):
		query = 'UPDATE users SET access_token = %s WHERE github_id = %s;'
		cursor = yield self.execute(query, user['access_token'], user['id'])
		return cursor.rowcount

	@tornado.gen.coroutine
	def set_contact_info(self, github_id, info_type, info):
		try:
			query = 'INSERT INTO contact_info (github_id, type, info) VALUES(%s, %s, %s);'
			yield self.execute(query, github_id, info_type, info)
		except psycopg2.IntegrityError:
			query = 'UPDATE contact_info SET info = %s WHERE github_id = %s AND type = %s;'
			yield self.execute(query, info, github_id, info_type)

	@tornado.gen.coroutine
	def update_questionnaire(self, github_id, q1, q2, q3, q4, q5):
		try:
			query = 'INSERT INTO questionnaire (github_id, q1, q2, q3, q4, q5) VALUES(%s, %s, %s, %s, %s, %s);'
			yield self.execute(query, github_id, q1, q2, q3, q4, q5)
		except psycopg2.IntegrityError:
			query = '''
				UPDATE questionnaire
				SET q1 = %s, q2 = %s, q3 = %s, q4 = %s, q5 = %s
				WHERE github_id = %s;
			'''
			yield self.execute(query, q1, q2, q3, q4, q5, github_id)

	@tornado.gen.coroutine
	def get_user(self, github_id):
		query = 'SELECT github_id, username, access_token, is_mentor FROM users WHERE github_id = %s;'
		cursor = yield self.execute(query, github_id)
		return cursor.fetchone()

	@tornado.gen.coroutine
	def get_user_by(self, field, value):
		query = 'SELECT github_id, username, access_token, is_mentor FROM users WHERE ' + field + ' = %s;'
		cursor = yield self.execute(query, value)
		return cursor.fetchone()

	@tornado.gen.coroutine
	def get_contact_info(self, github_id):
		query = 'SELECT type, info FROM contact_info WHERE github_id = %s;'
		cursor = yield self.execute(query, github_id)
		return cursor.fetchall()

	@tornado.gen.coroutine
	def get_questionnaire(self, github_id):
		# DESC sorts NULL first
		query = '''
			SELECT q1, q2, q3, q4, q5 FROM questionnaire
			WHERE github_id = %s OR github_id IS NULL
			ORDER BY github_id DESC;
		'''
		cursor = yield self.execute(query, github_id)
		questions = cursor.fetchone()
		answers = cursor.fetchone() or [""] * 5
		return questions, answers

	@tornado.gen.coroutine
	def get_userlist(self):
		query = '''
			SELECT users.username, mentors.username FROM users
			LEFT OUTER JOIN mentorships ON users.github_id = mentorships.mentee_id
			LEFT OUTER JOIN users AS mentors ON mentorships.mentor_id = mentors.github_id
			ORDER BY users.is_mentor DESC;
		'''
		cursor = yield self.execute(query)
		return cursor.fetchall()

	@tornado.gen.coroutine
	def get_mentor(self, github_id):
		query = '''
			SELECT github_id, username FROM users
			INNER JOIN mentorships ON users.github_id = mentorships.mentor_id
			WHERE mentorships.mentee_id = %s;
		'''
		cursor = yield self.execute(query, github_id)
		return cursor.fetchone()

	@tornado.gen.coroutine
	def get_mentees(self, mentor):
		query = '''
			SELECT github_id, username FROM users
			INNER JOIN mentorships ON users.github_id = mentorships.mentee_id
			WHERE mentorships.mentor_id = %s;
		'''
		cursor = yield self.execute(query, mentor['github_id'])
		return cursor.fetchall()

class ContactInfoType:
	EMAIL = 0
	IRC = 1
